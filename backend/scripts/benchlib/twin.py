"""Latency and token-cost twin for an eval run (T0.08).

Doctrine (``docs/planning/gate-ledger.md`` rule 2): accuracy never ships
without its twin. This module builds that twin for the retrieval eval path
without touching ``app/`` — everything here is either pure arithmetic
(percentiles, token accumulation) or a *spy*: a wrapper that times/observes
a shipping method and then calls straight through to it, installed for the
duration of one measured run and removed immediately after
(``instrument_retrieval``). Reimplementing a channel to time it would be a
fork, not a measurement; nothing here does that.

Composition, matching the split the rest of benchlib already uses:

- ``instrument_retrieval(llm)`` — a context manager. Wrap a call to
  ``retrieval_runner.run_retrieval(...)`` in it; the yielded
  ``LatencyRecorder`` has five populated channels afterwards:
  ``embed_query``, ``semantic_search``, ``keyword_search``, ``reranker``,
  ``end_to_end``. Call ``.stats()`` on it once the run is done.
- ``TwinningOrchestrator`` — a ``CachingLLMOrchestrator`` subclass. Use it
  in place of ``CachingLLMOrchestrator`` anywhere an eval run builds its
  LLM (``run_ingest``, ``run_retrieval`` both take any ``LLMOrchestrator``,
  so this is a drop-in swap). Its ``.tokens`` accumulates token usage by
  LLM purpose across whatever it is asked to do — ingest's
  extraction/classification calls and retrieval's reranker calls alike —
  and persists the usage envelope into the disk cache so a later warm
  replay can still report what the call cost when it was paid.
- ``Twin.capture(recorder, tokens)`` bundles both into one JSON-native
  structure. A non-retrieval arm measured against the same doctrine (the
  full-context baseline in ``full_context.py``) reuses ``LatencyRecorder``,
  ``TwinningOrchestrator`` and this constructor with its own
  ``declared_channels``, rather than growing a parallel counter.
- ``EvalRun`` pairs a ``retrieval_scorer.ScoreReport`` with a ``Twin`` and
  structurally refuses to exist without a real one — see its docstring.
  ``record_eval_run`` is the sanctioned way to append one to the ledger.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, is_dataclass
from typing import Sequence

from benchlib import ledger
from benchlib.caching_llm import CachingLLMOrchestrator, chat_content

from app.services.hybrid_search import HybridSearchService
from app.services.pipeline import ProcessingPipeline
from app.services.reranker import RerankerService

# ── percentiles ──────────────────────────────────────────────────────────

# p95 needs at least 1/(1 - 0.95) = 20 samples before the top 5% has even
# one genuine observation in it; below that, "p95" is describing a single
# sample's position, not a tail. One threshold covers p50 too (ruling 6:
# an under-powered distribution is reported as such, not with an asterisk
# on only the metric that happens to need more samples) -- mirrors
# retrieval_scorer.DEFAULT_MIN_PAIRS's same "powered" bit for the same
# reason.
MIN_SAMPLES_FOR_PERCENTILE = 20

PERCENTILE_METHOD = "nearest-rank"


def _nearest_rank(sorted_samples: list[float], pct: float) -> float:
    n = len(sorted_samples)
    rank = max(1, min(n, math.ceil(pct / 100.0 * n)))
    return sorted_samples[rank - 1]


@dataclass(frozen=True)
class PercentileStats:
    n: int
    powered: bool
    p50: float | None
    p95: float | None


def _percentile_stats(samples: list[float], min_samples: int) -> PercentileStats:
    n = len(samples)
    if n < min_samples:
        return PercentileStats(n=n, powered=False, p50=None, p95=None)
    ordered = sorted(samples)
    return PercentileStats(
        n=n, powered=True,
        p50=_nearest_rank(ordered, 50), p95=_nearest_rank(ordered, 95),
    )


# ── channel latency recording ───────────────────────────────────────────

# Channels whose samples may be served without any live model round trip,
# and which therefore carry a genuine two-population split (ruling 2).
# embed_query and reranker sit on CachingLLMOrchestrator's disk cache
# directly; end_to_end is a COMPOSITE whose window contains both of them,
# so a fully-cached query's end-to-end wall clock is disk-read time, not
# model time. Labelling every end_to_end sample "live" would blend two
# different systems' latencies into one p95 on a partly-warm run -- the
# exact merge ruling 2 forbids, one composite level up.
SPLIT_CHANNELS = ("embed_query", "reranker", "end_to_end")
# Pure Postgres round trips on every single call. No cache-served state
# exists for these to be confused with, so their `cache` bucket is empty
# by construction, not by omission.
DB_CHANNELS = ("semantic_search", "keyword_search")
CHANNELS = (*SPLIT_CHANNELS, *DB_CHANNELS)


@dataclass(frozen=True)
class ChannelStats:
    channel: str
    live: PercentileStats
    cache: PercentileStats


class LatencyRecorder:
    """Two labelled populations per channel: live (a real model or DB
    round trip happened) and cache (served from CachingLLMOrchestrator's
    disk cache with no round trip). Never merge the two -- CLAUDE.md /
    ruling 2: a warm run's disk-read time reported as if it were live
    model latency is a number that describes a system nobody runs.
    """

    def __init__(self):
        self._live: dict[str, list[float]] = defaultdict(list)
        self._cache: dict[str, list[float]] = defaultdict(list)

    def record(self, channel: str, elapsed_s: float, served_by: str) -> None:
        if served_by not in ("live", "cache"):
            raise ValueError(f"served_by must be 'live' or 'cache', got {served_by!r}")
        (self._live if served_by == "live" else self._cache)[channel].append(elapsed_s)

    def stats(
        self, *, min_samples: int = MIN_SAMPLES_FOR_PERCENTILE,
        declared_channels: Sequence[str] = CHANNELS,
    ) -> dict[str, ChannelStats]:
        """``declared_channels`` are always reported, at zero samples if the
        run never touched them -- an absent channel is stated, not omitted.
        A second arm measuring a different set of channels (the full-context
        baseline's ``full_context_call``) declares its own, so its twin does
        not carry five retrieval channels the arm structurally cannot have.
        """
        channels = set(self._live) | set(self._cache) | set(declared_channels)
        return {
            channel: ChannelStats(
                channel=channel,
                live=_percentile_stats(self._live.get(channel, []), min_samples),
                cache=_percentile_stats(self._cache.get(channel, []), min_samples),
            )
            for channel in channels
        }


def live_call_count(llm):
    """``None`` for an orchestrator with no call counter -- an unknown
    that must not be read as "no live call happened"."""
    return getattr(llm, "live_calls", None)


def served_by(before, after) -> str:
    """A sample is cache-served only when a counter existed on both sides
    of the window and did not move. An orchestrator without the counter
    reports "live", the conservative label: attributing an unmeasurable
    call to the cache population is what would understate a real p95."""
    return "cache" if (before is not None and after == before) else "live"


@contextmanager
def instrument_retrieval(llm):
    """Time the five channels ruling 1 names, for the duration of the
    ``with`` block, then restore the shipping classes verbatim.

    Not reentrant and not safe across concurrent measured runs in one
    process -- it patches ``HybridSearchService`` / ``RerankerService`` /
    ``ProcessingPipeline`` at the CLASS level (those are constructed fresh
    per call inside ``ProcessingPipeline.semantic_search``, so there is no
    live instance to patch ahead of time) and ``llm.embed`` at the
    instance level. Same constraint FROZEN.md already documents for
    ``CachingLLMOrchestrator.live_calls``: holds for sequential reuse of
    one call, not concurrent measured runs sharing this context manager.
    """
    recorder = LatencyRecorder()

    orig_semantic = HybridSearchService._semantic_search
    orig_keyword = HybridSearchService._keyword_search
    orig_rerank = RerankerService.rerank
    orig_pipeline_search = ProcessingPipeline.semantic_search
    orig_embed = llm.embed
    # A bound-method attribute access (``llm.embed``) is not itself an
    # instance attribute unless something already set one -- restoring by
    # deleting (when there was none) rather than reassigning is what makes
    # the object exactly as it was, not merely behaviourally equivalent.
    had_instance_embed = "embed" in vars(llm)

    async def spy_semantic(self, *args, **kwargs):
        t0 = time.perf_counter()
        result = await orig_semantic(self, *args, **kwargs)
        recorder.record("semantic_search", time.perf_counter() - t0, "live")
        return result

    async def spy_keyword(self, *args, **kwargs):
        t0 = time.perf_counter()
        result = await orig_keyword(self, *args, **kwargs)
        recorder.record("keyword_search", time.perf_counter() - t0, "live")
        return result

    async def spy_rerank(self, *args, **kwargs):
        # A batch-scored rerank call mixes cache-hit and live documents;
        # there is no single-call granularity finer than "did any live
        # round trip happen at all" (mirrors embed_batch's own "any miss
        # increments live_calls by exactly 1" population semantics).
        before = live_call_count(self.llm)
        t0 = time.perf_counter()
        result = await orig_rerank(self, *args, **kwargs)
        elapsed = time.perf_counter() - t0
        recorder.record("reranker", elapsed, served_by(before, live_call_count(self.llm)))
        return result

    async def spy_pipeline_search(self, *args, **kwargs):
        # The composite window: whether THIS query paid for a live model
        # call anywhere inside it (its query embed, any reranker call) is
        # what decides which system's latency the sample describes.
        before = live_call_count(llm)
        t0 = time.perf_counter()
        result = await orig_pipeline_search(self, *args, **kwargs)
        elapsed = time.perf_counter() - t0
        recorder.record("end_to_end", elapsed, served_by(before, live_call_count(llm)))
        return result

    async def spy_embed(text):
        before = live_call_count(llm)
        t0 = time.perf_counter()
        result = await orig_embed(text)
        elapsed = time.perf_counter() - t0
        recorder.record("embed_query", elapsed, served_by(before, live_call_count(llm)))
        return result

    HybridSearchService._semantic_search = spy_semantic
    HybridSearchService._keyword_search = spy_keyword
    RerankerService.rerank = spy_rerank
    ProcessingPipeline.semantic_search = spy_pipeline_search
    llm.embed = spy_embed

    try:
        yield recorder
    finally:
        HybridSearchService._semantic_search = orig_semantic
        HybridSearchService._keyword_search = orig_keyword
        RerankerService.rerank = orig_rerank
        ProcessingPipeline.semantic_search = orig_pipeline_search
        if had_instance_embed:
            llm.embed = orig_embed
        else:
            del llm.embed


# ── token-cost attribution ──────────────────────────────────────────────


def _cached_prompt_tokens(usage: dict) -> int:
    """Mirrors LLMOrchestrator._log_usage's vendor-field fallback order
    (llm.py: OpenAI's prompt_tokens_details.cached_tokens, DeepSeek's
    prompt_cache_hit_tokens, a generic cached_tokens) so the twin reports
    the same cache-hit figure the live log line already surfaces."""
    details = usage.get("prompt_tokens_details")
    if isinstance(details, dict) and details.get("cached_tokens"):
        return details["cached_tokens"]
    return usage.get("prompt_cache_hit_tokens") or usage.get("cached_tokens") or 0


@dataclass
class PurposeUsage:
    live_calls: int = 0
    live_prompt_tokens: int = 0
    live_completion_tokens: int = 0
    live_cached_prompt_tokens: int = 0
    # Live calls the vendor reported no usage envelope for -- the Ollama
    # chat path only calls _log_usage when prompt_eval_count/eval_count
    # are present (app/services/llm.py), so a purpose pointed at Ollama
    # produces genuinely unmeasured calls. Without this marker
    # `live_calls=94, live_prompt_tokens=0` is indistinguishable from 94
    # calls that really summed to zero, which is ruling 3's "unknown
    # coerced into a zero-looking total" one bucket over. Symmetric with
    # cache_unknown_calls below.
    live_unknown_calls: int = 0
    # Replayed from a cache entry that itself carries a persisted usage
    # envelope (written by this class or a later one) -- a genuine,
    # known cost paid on some earlier run, not billed again just now.
    cache_known_calls: int = 0
    cache_known_prompt_tokens: int = 0
    cache_known_completion_tokens: int = 0
    cache_known_cached_prompt_tokens: int = 0
    # Replayed from a cache entry with no usage attached -- either a
    # bare pre-T0.08 string, or a call the vendor itself never reported
    # usage for. Its cold-equivalent cost is genuinely unknown; ruling 3
    # forbids reporting it as zero, so it is counted here and nowhere
    # else, and a consumer must render it as "unknown", not sum it in.
    cache_unknown_calls: int = 0


class TokenLedger:
    def __init__(self):
        self._by_purpose: dict[str, PurposeUsage] = defaultdict(PurposeUsage)

    def record_live(self, purpose: str, usage: dict | None) -> None:
        bucket = self._by_purpose[purpose]
        bucket.live_calls += 1
        if not usage:
            bucket.live_unknown_calls += 1
            return
        bucket.live_prompt_tokens += usage.get("prompt_tokens", 0) or 0
        bucket.live_completion_tokens += usage.get("completion_tokens", 0) or 0
        bucket.live_cached_prompt_tokens += _cached_prompt_tokens(usage)

    def record_cache_known(self, purpose: str, usage: dict) -> None:
        bucket = self._by_purpose[purpose]
        bucket.cache_known_calls += 1
        bucket.cache_known_prompt_tokens += usage.get("prompt_tokens", 0) or 0
        bucket.cache_known_completion_tokens += usage.get("completion_tokens", 0) or 0
        bucket.cache_known_cached_prompt_tokens += _cached_prompt_tokens(usage)

    def record_cache_unknown(self, purpose: str) -> None:
        self._by_purpose[purpose].cache_unknown_calls += 1

    def as_dict(self) -> dict[str, dict]:
        return {purpose: asdict(usage) for purpose, usage in self._by_purpose.items()}


class TwinningOrchestrator(CachingLLMOrchestrator):
    """``CachingLLMOrchestrator`` extended (never forked) to capture token
    usage per LLM purpose and persist it alongside the cached chat
    response, so a replayed call can report what it cost when it was
    paid (ruling 3).

    Capture point: ``LLMOrchestrator._log_usage`` is called by ``self.``
    on both api_kind paths (llm.py:301 openai-compat, :379 ollama) right
    before the content is returned, so overriding it here sees every live
    chat call regardless of vendor -- no ``app/`` change needed (ruling 1
    / brief §3).

    Backward compatibility: a chat cache entry written before this class
    existed is a bare JSON string (the raw content, ``caching_llm.py``'s
    original format). This class writes ``{"content": ..., "usage": ...}``
    instead, but a bare-string hit still reads back as its content with no
    error -- it has no usage to report, and that gap is counted as
    ``cache_unknown``, never coerced to a paid-zero.
    """

    def __init__(self, config, cache_dir: str):
        super().__init__(config, cache_dir)
        self.tokens = TokenLedger()
        self._last_usage: dict | None = None

    def _log_usage(self, purpose: str, model: str, usage: dict | None) -> None:
        super()._log_usage(purpose, model, usage)
        self._last_usage = usage

    async def chat_completion(self, purpose, messages, **kwargs):
        key = self._chat_key(purpose, messages, kwargs)
        hit = self._read(key)
        if hit is not None:
            return self._replay_chat_hit(purpose, hit)

        self.live_calls += 1
        self._last_usage = None
        content = await self._live_chat(purpose, messages, **kwargs)
        usage = self._last_usage
        self.tokens.record_live(purpose, usage)
        self._write(key, {"content": content, "usage": usage})
        return content

    def _replay_chat_hit(self, purpose: str, hit) -> str:
        usage = hit.get("usage") if isinstance(hit, dict) else None
        if usage:
            self.tokens.record_cache_known(purpose, usage)
        else:
            self.tokens.record_cache_unknown(purpose)
        return chat_content(hit)


# ── the twin, and the structural no-twin-no-accuracy guard ─────────────


@dataclass(frozen=True)
class Twin:
    channels: dict[str, ChannelStats]
    tokens_by_purpose: dict[str, dict]
    percentile_method: str = PERCENTILE_METHOD
    min_samples_for_percentile: int = MIN_SAMPLES_FOR_PERCENTILE

    def __post_init__(self):
        # Presence of TYPE is not presence of MEASUREMENT: a Twin with no
        # channels at all satisfies EvalRun's isinstance guard while
        # carrying nothing, which is the twin-less emission ruling 5
        # forbids wearing the right class. Enforced here rather than in
        # EvalRun so a vacuous Twin cannot be constructed at all. A
        # channel with zero samples is fine and expected (a disabled
        # reranker) -- what is refused is having no channels.
        if not self.channels:
            raise ValueError(
                "Twin carries no channels: an empty twin is not a "
                "measurement. Build it with Twin.capture(recorder, tokens), "
                "which always emits every declared channel."
            )

    @classmethod
    def capture(
        cls, recorder: LatencyRecorder, tokens: TokenLedger,
        *, min_samples: int = MIN_SAMPLES_FOR_PERCENTILE,
        declared_channels: Sequence[str] = CHANNELS,
    ) -> "Twin":
        return cls(
            channels=recorder.stats(
                min_samples=min_samples, declared_channels=declared_channels,
            ),
            tokens_by_purpose=tokens.as_dict(),
            min_samples_for_percentile=min_samples,
        )

    def to_ledger_payload(self) -> dict:
        return {
            "percentile_method": self.percentile_method,
            "min_samples_for_percentile": self.min_samples_for_percentile,
            "channels": {
                name: {"live": asdict(stats.live), "cache": asdict(stats.cache)}
                for name, stats in self.channels.items()
            },
            "tokens_by_purpose": self.tokens_by_purpose,
        }


@dataclass(frozen=True)
class EvalRun:
    """Pairs a scored accuracy run with its twin. Doctrine (gate-ledger.md
    rule 2): accuracy never ships without its twin -- so there is no
    argument shape that produces an ``EvalRun`` with a missing or fake
    twin. This is deliberately not a warning a caller could ignore: the
    object never comes into existence without one. T0.09/T0.10 are meant
    to build their scored run through this constructor and
    ``record_eval_run`` below, not through a raw dict handed to
    ``benchlib.ledger.record``.
    """
    score: object
    twin: Twin

    def __post_init__(self):
        if not isinstance(self.twin, Twin):
            raise TypeError(
                "EvalRun requires a real Twin (latency + token-cost); got "
                f"{self.twin!r} instead. Accuracy never ships without its "
                "twin -- gate-ledger.md rule 2."
            )

    def to_ledger_payload(self) -> dict:
        score_payload = asdict(self.score) if is_dataclass(self.score) else self.score
        return {"score": score_payload, "twin": self.twin.to_ledger_payload()}


def record_eval_run(eval_run: EvalRun, path=ledger.DEFAULT_PATH) -> None:
    """The sanctioned way to append an accuracy-bearing run to the
    ledger. Takes only an ``EvalRun`` -- whose constructor already
    refused to exist without a twin -- so there is no call here that
    could record accuracy metrics without one attached."""
    ledger.record(eval_run.to_ledger_payload(), path=path)

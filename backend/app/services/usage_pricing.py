"""Model prices, and the arithmetic that turns tokens into money.

Pure: no session, no I/O, no clock. The caller resolves the override dict from
the ``model_prices`` config row and passes it in, exactly as
``get_feature_flags_dict`` merges a DB row over ``FEATURE_FLAGS_DEFAULTS``.

**Three rates, not two.** A cached input token bills at roughly 5% of input on
DeepSeek and 50% on OpenAI, so a single input rate would be wrong by up to
twentyfold on the one axis most worth optimising. The per-vendor cache
semantics are catalogued in ``LLMOrchestrator._log_usage``'s docstring, which
also records that Anthropic's caching never fires on the OpenAI-compat path
this orchestrator dispatches it over — so an Anthropic row must not carry a
cache discount.

Rates are micro-USD per million tokens. Money is an integer end to end;
``memories.confidence`` being REAL is not a precedent for currency.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

_RATE_FIELDS = (
    "input_micros_per_mtok",
    "cached_micros_per_mtok",
    "output_micros_per_mtok",
)


@dataclass(frozen=True)
class ModelRates:
    input_micros_per_mtok: int
    cached_micros_per_mtok: int
    output_micros_per_mtok: int


#: Shipped defaults for the models this deployment actually resolves. A model
#: absent here prices to None — surfaced as "not priced" with the model named,
#: never as free. The local Ollama entries are a *measured* zero, which is a
#: different state from absent and must stay distinguishable.
DEFAULT_MODEL_PRICES: dict[str, ModelRates] = {
    "deepseek-v4-flash": ModelRates(270_000, 14_000, 1_100_000),
    "deepseek-v4-pro": ModelRates(550_000, 28_000, 2_190_000),
    "gpt-5.5": ModelRates(1_250_000, 625_000, 10_000_000),
    "qwen3-embedding:0.6b": ModelRates(0, 0, 0),
    "nomic-embed-text:latest": ModelRates(0, 0, 0),
}


def resolve_rates(model: str, overrides: dict) -> ModelRates | None:
    """The operator's row merged over the shipped default, per model.

    A partial override keeps the shipped values for the rates it does not
    mention: someone correcting one number must not silently zero the others.
    """
    base = DEFAULT_MODEL_PRICES.get(model)
    over = overrides.get(model)
    if over is None:
        return base
    fields = {k: int(v) for k, v in over.items() if k in _RATE_FIELDS}
    if base is None:
        try:
            return ModelRates(**fields)
        except TypeError:
            # A partial override for a model with no shipped default cannot be
            # completed, and inventing the missing rates would be worse than
            # reporting the call unpriced.
            return None
    return replace(base, **fields)


def compute_cost_micros(
    rates: ModelRates | None,
    prompt: int | None,
    cached: int | None,
    completion: int | None,
) -> int | None:
    """Micro-USD for one call, or None when it cannot be priced.

    ``cached`` is a *subset* of ``prompt`` as every vendor reports it, so the
    fresh portion is ``prompt - cached``. Treating it as an addition would
    double-count the cache hit it is supposed to celebrate.
    """
    if rates is None or prompt is None:
        return None
    cached_t = cached or 0
    fresh = max(0, prompt - cached_t)
    out = completion or 0
    total = (
        fresh * rates.input_micros_per_mtok
        + cached_t * rates.cached_micros_per_mtok
        + out * rates.output_micros_per_mtok
    )
    return total // 1_000_000

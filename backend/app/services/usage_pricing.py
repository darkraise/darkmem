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


#: The `config` row the operator's price edits live in. Prices are config, not
#: schema: a vendor changing its rate must not need a migration, and a
#: deployment on a discount must not need a fork.
MODEL_PRICES_CONFIG_KEY = "model_prices"


def normalise_price_overrides(raw: dict) -> dict[str, dict[str, int]]:
    """Validate an operator-supplied price table, or raise ``ValueError``.

    Rejects rather than drops. An unknown rate field silently ignored leaves an
    operator looking at a form that accepted their number and did nothing with
    it, and a negative rate produces a negative cost -- a total a per-model edit
    can drive below zero is not a total.
    """
    if not isinstance(raw, dict):
        raise ValueError("prices must be an object keyed by model name")
    out: dict[str, dict[str, int]] = {}
    for model, rates in raw.items():
        if not isinstance(rates, dict):
            raise ValueError(f"{model}: rates must be an object")
        unknown = set(rates) - set(_RATE_FIELDS)
        if unknown:
            raise ValueError(f"{model}: unknown rate field(s) {sorted(unknown)}")
        clean: dict[str, int] = {}
        for field, value in rates.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{model}.{field}: rate must be a number")
            if value < 0:
                raise ValueError(f"{model}.{field}: rate must not be negative")
            clean[field] = int(value)
        out[model] = clean
    return out


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

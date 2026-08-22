from app.services.usage_pricing import (
    DEFAULT_MODEL_PRICES,
    ModelRates,
    compute_cost_micros,
    resolve_rates,
)

RATES = ModelRates(input_micros_per_mtok=270_000,
                   cached_micros_per_mtok=14_000,
                   output_micros_per_mtok=1_100_000)


def test_cached_tokens_are_billed_at_the_cached_rate():
    """A cached input token bills at ~5% on DeepSeek. Charging it at the input
    rate would overstate a cache hit by twentyfold -- and cache-hit rate is the
    single biggest lever this feature exists to expose."""
    all_fresh = compute_cost_micros(RATES, prompt=1_000_000, cached=0, completion=0)
    all_cached = compute_cost_micros(RATES, prompt=1_000_000, cached=1_000_000, completion=0)
    assert all_fresh == 270_000
    assert all_cached == 14_000


def test_cached_is_a_subset_of_prompt_not_an_addition():
    """Vendors report cached_tokens as part of prompt_tokens, not beside it."""
    half = compute_cost_micros(RATES, prompt=1_000_000, cached=500_000, completion=0)
    assert half == 135_000 + 7_000


def test_unmeasured_tokens_price_to_none_never_zero():
    assert compute_cost_micros(RATES, prompt=None, cached=None, completion=None) is None


def test_unknown_model_has_no_rates():
    assert resolve_rates("some-model-we-never-shipped", {}) is None


def test_operator_override_wins_over_the_shipped_default():
    """Prices follow the feature_flags pattern: a DB row merged over defaults."""
    model = next(iter(DEFAULT_MODEL_PRICES))
    over = {model: {"input_micros_per_mtok": 1, "cached_micros_per_mtok": 1,
                    "output_micros_per_mtok": 1}}
    assert resolve_rates(model, over).input_micros_per_mtok == 1
    assert resolve_rates(model, {}) == DEFAULT_MODEL_PRICES[model]


def test_a_partial_override_keeps_the_other_shipped_rates():
    """An operator correcting one rate must not silently zero the other two."""
    model = "deepseek-v4-flash"
    got = resolve_rates(model, {model: {"output_micros_per_mtok": 999}})
    assert got.output_micros_per_mtok == 999
    assert got.input_micros_per_mtok == DEFAULT_MODEL_PRICES[model].input_micros_per_mtok


def test_a_local_model_is_priced_at_a_measured_zero():
    """Free is a measured value and must not read as 'unpriced'."""
    rates = resolve_rates("qwen3-embedding:0.6b", {})
    assert rates is not None
    assert compute_cost_micros(rates, prompt=5_000, cached=0, completion=0) == 0

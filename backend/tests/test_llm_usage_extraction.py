import ast
from pathlib import Path

from app.services.llm import extract_usage
from app.services.llm_quirks import quirks_for


def test_cache_hit_field_is_read_from_the_quirk_row_not_a_vendor_branch():
    """Vendors put the cached count in different places. A call site comparing
    api_kind to a vendor name fails tests/test_api_kind_dispatch.py, so the
    field names live on the quirk row."""
    assert "prompt_cache_hit_tokens" in quirks_for("deepseek").cache_hit_fields
    assert any("cached_tokens" in f for f in quirks_for("openai").cache_hit_fields)


def test_anthropic_declares_no_cache_field():
    """Its caching needs the native /v1/messages path with explicit
    cache_control markers; on the compat path this orchestrator uses it never
    fires, so a cache discount here would be fiction."""
    assert quirks_for("anthropic").cache_hit_fields == ()


def test_extracts_the_openai_nested_cache_field():
    got = extract_usage(
        {"usage": {"prompt_tokens": 100,
                   "completion_tokens": 10,
                   "prompt_tokens_details": {"cached_tokens": 80}}},
        quirks_for("openai"))
    assert got["prompt_tokens"] == 100
    assert got["cached_tokens"] == 80
    assert got["completion_tokens"] == 10


def test_extracts_the_deepseek_flat_cache_field():
    got = extract_usage(
        {"usage": {"prompt_tokens": 100, "completion_tokens": 5,
                   "prompt_cache_hit_tokens": 90}},
        quirks_for("deepseek"))
    assert got["cached_tokens"] == 90


def test_extracts_ollama_native_counts_from_the_done_chunk():
    got = extract_usage({"prompt_eval_count": 42, "eval_count": 7, "done": True},
                        quirks_for("ollama"))
    assert got["prompt_tokens"] == 42
    assert got["completion_tokens"] == 7


def test_a_missing_envelope_is_none_not_zeros():
    """The doctrine benchlib/twin.py sets: a number nobody observed is not 0."""
    assert extract_usage({"choices": []}, quirks_for("openai")) is None


def test_reasoning_tokens_are_broken_out_when_present():
    got = extract_usage(
        {"usage": {"prompt_tokens": 10, "completion_tokens": 500,
                   "completion_tokens_details": {"reasoning_tokens": 480}}},
        quirks_for("openai"))
    assert got["reasoning_tokens"] == 480


def test_the_whole_envelope_is_retained():
    """Flattening to four integers makes a question nobody has asked yet
    unanswerable against history that was already paid for."""
    env = {"prompt_tokens": 10, "completion_tokens": 2, "some_future_field": 7}
    got = extract_usage({"usage": env}, quirks_for("openai"))
    assert got["raw"] == env


def test_no_vendor_literal_was_introduced_in_llm_py():
    """tests/test_api_kind_dispatch.py enforces this build-wide; assert it here
    too so a regression names this task."""
    tree = ast.parse(Path("app/services/llm.py").read_text())
    vendors = {"openai", "ollama", "anthropic", "deepseek", "google", "zai"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and sub.value in vendors:
                    raise AssertionError(f"vendor literal in a comparison at line {node.lineno}")

"""``api_kind`` is the only place a vendor quirk lives (doc 11 §4).

Two halves: every declared kind dispatches correctly through the shared
orchestrator, and each recorded vendor quirk has a regression test that fails
if the quirk is removed.
"""

import ast
import json
from pathlib import Path
from typing import get_args

import httpx
import pytest

from app.config import LLMApiKind, LLMPurposeConfig
from app.services.llm import LLMOrchestrator
from app.services.llm_quirks import (
    ANTHROPIC_VERSION,
    assert_reasoning_effort,
    known_api_kinds,
    quirks_for,
)

COMPAT_KINDS = ("openai", "anthropic", "google", "deepseek", "zai")
EMBEDDING_KINDS = ("openai", "ollama", "google", "zai")
NO_EMBEDDING_KINDS = ("anthropic", "deepseek")


def _orchestrator(handler, **purpose_kwargs) -> LLMOrchestrator:
    cfg = LLMPurposeConfig(base_url="http://mock/v1", model="m", **purpose_kwargs)
    llm = LLMOrchestrator({"extraction": cfg, "embedding": cfg})
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return llm


class Captured:
    """Records the one request the mock transport saw."""

    def __init__(self, response: dict):
        self.request: httpx.Request | None = None
        self._response = response

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.request = request
        return httpx.Response(200, json=self._response)

    @property
    def body(self) -> dict:
        assert self.request is not None
        return json.loads(self.request.content)


def _chat_capture() -> Captured:
    return Captured({"choices": [{"message": {"content": "ok"}}]})


async def _chat(api_kind: str, **kwargs) -> Captured:
    capture = _chat_capture()
    llm = _orchestrator(capture, api_kind=api_kind, **kwargs)
    await llm.chat_completion("extraction", [{"role": "user", "content": "hi"}], seed=7)
    await llm.close()
    return capture


# ── every declared kind dispatches ────────────────────────────────────


def test_quirk_table_covers_every_declared_api_kind():
    assert set(known_api_kinds()) == set(get_args(LLMApiKind))


@pytest.mark.parametrize("api_kind", COMPAT_KINDS)
async def test_compat_kinds_post_to_chat_completions(api_kind):
    capture = await _chat(api_kind)
    assert str(capture.request.url) == "http://mock/v1/chat/completions"
    assert capture.body["model"] == "m"


async def test_ollama_posts_to_the_native_chat_endpoint():
    capture = Captured({"message": {"content": "ok"}})
    llm = _orchestrator(capture, api_kind="ollama")
    await llm.chat_completion(
        "extraction",
        [{"role": "user", "content": "hi"}],
        response_format={"type": "json_object"},
        seed=7,
    )
    await llm.close()
    assert str(capture.request.url) == "http://mock/api/chat"
    body = capture.body
    assert body["think"] is False
    assert body["format"] == "json"
    assert body["options"]["seed"] == 7


@pytest.mark.parametrize("api_kind", EMBEDDING_KINDS)
async def test_embedding_kinds_reach_their_embed_endpoint(api_kind):
    native = quirks_for(api_kind).native_protocol
    payload = (
        {"embeddings": [[0.1, 0.2]]} if native else {"data": [{"embedding": [0.1, 0.2]}]}
    )
    capture = Captured(payload)
    llm = _orchestrator(capture, api_kind=api_kind)
    vector, fingerprint = await llm.embed("hello")
    await llm.close()
    assert vector == [0.1, 0.2]
    assert fingerprint == "m|2"
    expected = "http://mock/api/embed" if native else "http://mock/v1/embeddings"
    assert str(capture.request.url) == expected


@pytest.mark.parametrize("api_kind", NO_EMBEDDING_KINDS)
async def test_embed_on_a_no_embeddings_vendor_fails_before_the_request(api_kind):
    capture = Captured({"data": [{"embedding": [0.1]}]})
    llm = _orchestrator(capture, api_kind=api_kind)
    with pytest.raises(RuntimeError, match="no embeddings endpoint"):
        await llm.embed("hello")
    with pytest.raises(RuntimeError, match="no embeddings endpoint"):
        await llm.embed_batch(["hello"])
    await llm.close()
    assert capture.request is None


# ── recorded quirk 1: Anthropic auth is x-api-key, not Bearer ──────────


async def test_anthropic_authenticates_with_x_api_key_and_version():
    capture = await _chat("anthropic", api_key="sk-test")
    headers = capture.request.headers
    assert headers["x-api-key"] == "sk-test"
    assert headers["anthropic-version"] == ANTHROPIC_VERSION
    assert "authorization" not in headers


@pytest.mark.parametrize("api_kind", ("openai", "google", "deepseek", "zai"))
async def test_compat_vendors_authenticate_with_bearer(api_kind):
    capture = await _chat(api_kind, api_key="sk-test")
    headers = capture.request.headers
    assert headers["authorization"] == "Bearer sk-test"
    assert "x-api-key" not in headers


async def test_anthropic_drops_response_format_and_seed():
    capture = _chat_capture()
    llm = _orchestrator(capture, api_kind="anthropic")
    await llm.chat_completion(
        "extraction",
        [{"role": "user", "content": "hi"}],
        response_format={"type": "json_object"},
        seed=7,
    )
    await llm.close()
    assert "response_format" not in capture.body
    assert "seed" not in capture.body


# ── recorded quirk 2: DeepSeek needs thinking:{type:disabled} ──────────


async def test_deepseek_disables_hidden_reasoning_with_the_thinking_flag():
    capture = await _chat("deepseek", reasoning=False)
    assert capture.body["thinking"] == {"type": "disabled"}


async def test_deepseek_enables_thinking_for_a_reasoning_purpose():
    capture = await _chat("deepseek", reasoning=True)
    assert capture.body["thinking"] == {"type": "enabled"}


async def test_zai_carries_the_same_thinking_flag():
    capture = await _chat("zai", reasoning=False)
    assert capture.body["thinking"] == {"type": "disabled"}


# ── recorded quirk 3: Gemini honours only reasoning_effort=none ────────


async def test_google_disables_reasoning_with_effort_none_and_no_thinking():
    capture = await _chat("google", reasoning=False)
    body = capture.body
    assert body["reasoning_effort"] == "none"
    # The compat shim rejects thinking:{type:disabled}; sending it 400s.
    assert "thinking" not in body


async def test_google_leaves_a_reasoning_purpose_alone():
    capture = await _chat("google", reasoning=True)
    assert "reasoning_effort" not in capture.body


async def test_google_does_not_override_a_configured_effort():
    capture = await _chat("google", reasoning=False, params={"reasoning_effort": "low"})
    assert capture.body["reasoning_effort"] == "low"


async def test_no_effort_is_injected_for_vendors_without_that_knob():
    # `openai` left this list 2026-08-25: gpt-5-family models reason by
    # default, so it gained `reasoning_disable_effort="none"` like google.
    # deepseek and zai disable through `thinking`, anthropic needs nothing.
    for api_kind in ("deepseek", "zai", "anthropic"):
        capture = await _chat(api_kind, reasoning=False)
        assert "reasoning_effort" not in capture.body, api_kind


# ── recorded quirk 4: OpenAI dropped `minimal` from the effort set ─────


def test_minimal_is_not_in_the_openai_effort_set():
    assert "minimal" not in quirks_for("openai").reasoning_efforts
    assert "minimal" in quirks_for("openai").retired_reasoning_efforts


async def test_openai_rejects_the_retired_minimal_effort():
    with pytest.raises(RuntimeError, match="retired reasoning_effort='minimal'"):
        await _chat("openai", params={"reasoning_effort": "minimal"})


async def test_openai_accepts_a_live_effort_value():
    capture = await _chat("openai", params={"reasoning_effort": "xhigh"})
    assert capture.body["reasoning_effort"] == "xhigh"


async def test_anthropic_rejects_reasoning_effort_entirely():
    with pytest.raises(RuntimeError, match="accepts no 'reasoning_effort'"):
        await _chat("anthropic", params={"reasoning_effort": "high"})


async def test_an_unrecorded_effort_vocabulary_passes_through():
    # DeepSeek documents reasoning_effort but we have not recorded its full
    # set; validating against a set we never verified would reject working
    # configs, so an unrecorded vocabulary is forwarded untouched.
    capture = await _chat("deepseek", params={"reasoning_effort": "low"})
    assert capture.body["reasoning_effort"] == "low"


# ── the output-cap key is a quirk too ─────────────────────────────────


@pytest.mark.parametrize(
    "api_kind,expected",
    [
        ("openai", "max_completion_tokens"),
        ("ollama", "num_predict"),
        ("anthropic", "max_tokens"),
        ("google", "max_tokens"),
        ("deepseek", "max_tokens"),
        ("zai", "max_tokens"),
    ],
)
def test_output_cap_key_per_vendor(api_kind, expected):
    assert quirks_for(api_kind).output_cap_key == expected


# ── no vendor conditional survives at any call site ───────────────────

_QUIRK_MODULE = Path("app/services/llm_quirks.py")


def _string_constants(node: ast.AST) -> list[str]:
    out: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            out.append(child.value)
    return out


def test_no_vendor_conditional_at_any_call_site():
    """Only the quirk table may compare anything to a vendor name.

    A branch on a vendor literal anywhere else is the drift this task exists
    to prevent: the quirk stops being one auditable row and becomes a rule
    two files disagree about.
    """
    vendors = set(known_api_kinds())
    app_root = Path(__file__).resolve().parents[1] / "app"
    offenders: list[str] = []
    for path in sorted(app_root.rglob("*.py")):
        if path.relative_to(app_root.parent) == _QUIRK_MODULE:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            named = set(_string_constants(node)) & vendors
            if named:
                rel = path.relative_to(app_root.parent)
                offenders.append(f"{rel}:{node.lineno} compares against {sorted(named)}")
    assert offenders == [], "vendor conditionals outside the quirk table:\n" + "\n".join(
        offenders
    )


# ── recorded quirk 5: `/no_think` is opt-in, not universal ─────────────
#
# Measured 2026-08-25: it used to be appended to every non-reasoning compat
# prompt. It is a qwen chat-template directive; OpenAI, Anthropic, Gemini,
# DeepSeek and GLM have never defined it, so for them it was literal text
# glued to the user's last message.


@pytest.mark.parametrize("api_kind", ["openai", "anthropic", "google", "deepseek", "zai"])
async def test_no_think_is_not_appended_by_default(api_kind):
    capture = await _chat(api_kind, reasoning=False)
    assert capture.body["messages"][-1]["content"] == "hi"


async def test_a_purpose_can_opt_into_the_no_think_directive():
    """A qwen model behind an OpenAI-compatible endpoint still wants it."""
    capture = await _chat(
        "openai", reasoning=False, params={"prompt_no_think": True},
    )
    assert capture.body["messages"][-1]["content"] == "hi /no_think"


async def test_the_opt_in_param_never_reaches_the_wire():
    """It steers the prompt; as a body field it is an unknown key."""
    capture = await _chat(
        "openai", reasoning=False, params={"prompt_no_think": True},
    )
    assert "prompt_no_think" not in capture.body


async def test_no_think_is_not_appended_to_a_reasoning_purpose():
    capture = await _chat(
        "openai", reasoning=True, params={"prompt_no_think": True},
    )
    assert capture.body["messages"][-1]["content"] == "hi"


# ── recorded quirk 6: OpenAI reasons by default too ───────────────────


async def test_openai_disables_reasoning_with_effort_none():
    capture = await _chat("openai", reasoning=False)
    assert capture.body["reasoning_effort"] == "none"


async def test_openai_does_not_override_a_configured_effort():
    capture = await _chat(
        "openai", reasoning=False, params={"reasoning_effort": "low"},
    )
    assert capture.body["reasoning_effort"] == "low"


async def test_openai_leaves_a_reasoning_purpose_alone():
    capture = await _chat("openai", reasoning=True)
    assert "reasoning_effort" not in capture.body


async def test_every_injected_disable_effort_is_in_its_own_vendor_vocabulary():
    """The injection is validated, not only the operator's own value.

    A mistyped `reasoning_disable_effort` in the quirk table would otherwise
    ship a 400 to production instead of raising locally.
    """
    for api_kind in known_api_kinds():
        quirks = quirks_for(api_kind)
        if quirks.reasoning_disable_effort is None:
            continue
        assert_reasoning_effort(api_kind, quirks.reasoning_disable_effort)

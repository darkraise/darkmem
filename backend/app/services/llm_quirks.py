"""Per-``api_kind`` vendor quirks — the one place a vendor is named.

Doc 11 §4 fixes ``api_kind`` as the sole axis a vendor difference may be
expressed on: auth scheme, reasoning-disable knob, structured-output caveat,
missing embeddings endpoint, model-probe path, and output-cap key all resolve
through the table below. Call sites ask this module a question about a
capability; they never compare ``api_kind`` to a vendor name themselves, which
is what keeps the rest of the codebase provider-agnostic.

Adding a vendor is four steps (doc 11 §4): extend ``LLMApiKind`` in
``app/config.py``, add its row here, add the row to doc 11 §4's table, and add
a seed default in ``llm_seed.py``.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

# Anthropic pins the wire format by date rather than by URL version segment;
# a request without it is rejected outright.
ANTHROPIC_VERSION = "2023-06-01"

AUTH_BEARER = "bearer"
AUTH_X_API_KEY = "x_api_key"


@dataclass(frozen=True)
class VendorQuirks:
    """Everything that differs between vendors, on one axis.

    ``reasoning_efforts`` is the recorded vocabulary for the vendor's
    ``reasoning_effort`` param; an empty tuple means "accepted but the full
    set is not recorded", so values pass through unvalidated. Enforcing a set
    we have not verified would reject working configs.
    """

    auth: str = AUTH_BEARER
    auth_extra_headers: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    # Ollama speaks its own protocol (/api/chat, /api/embed); every other kind
    # goes through the OpenAI-compatible surface today.
    native_protocol: bool = False
    supports_embedding: bool = True
    accepts_response_format: bool = True
    honours_seed: bool = True
    # ``thinking: {"type": enabled|disabled}`` is the only flag observed to
    # zero the hidden reasoning trace on these vendors.
    thinking_flag: bool = False
    accepts_reasoning_effort: bool = True
    reasoning_efforts: tuple[str, ...] = ()
    retired_reasoning_efforts: tuple[str, ...] = ()
    # The effort value that disables hidden chain-of-thought, injected for
    # non-reasoning purposes when the config does not set one.
    reasoning_disable_effort: str | None = None
    output_cap_key: str = "max_tokens"
    requires_api_key: bool = True
    # Whether the compat streaming body accepts
    # ``stream_options: {"include_usage": true}``. Without it a streamed
    # response carries no usage envelope at all, and chat generation cost is
    # unmeasurable rather than merely unrecorded.
    stream_usage_option: bool = False
    # Where this vendor reports the cached-input count, in the order to try.
    # Dotted paths descend into nested objects. Empty means the vendor
    # surfaces none: z.ai through the compat path, and Anthropic, whose
    # caching needs the native endpoint this orchestrator does not use.
    cache_hit_fields: tuple[str, ...] = ()


_QUIRKS: dict[str, VendorQuirks] = {
    "openai": VendorQuirks(
        # gpt-5-family models reject the legacy ``max_tokens``.
        output_cap_key="max_completion_tokens",
        # ``minimal`` was removed from the effort set by OpenAI; a config that
        # still carries it 400s on every request.
        reasoning_efforts=("none", "low", "medium", "high", "xhigh"),
        retired_reasoning_efforts=("minimal",),
        stream_usage_option=True,
        cache_hit_fields=("prompt_tokens_details.cached_tokens",),
    ),
    "ollama": VendorQuirks(
        native_protocol=True,
        output_cap_key="num_predict",
        requires_api_key=False,
        # Native protocol: the counts ride the ``done`` chunk, not an envelope
        # requested up front.
        stream_usage_option=False,
    ),
    "anthropic": VendorQuirks(
        auth=AUTH_X_API_KEY,
        auth_extra_headers=MappingProxyType({"anthropic-version": ANTHROPIC_VERSION}),
        supports_embedding=False,
        # The compat shim demands a strict ``json_schema``; the loose
        # ``json_object`` form every other vendor accepts is a 400 here, and
        # extraction encodes its schema in the prompt rather than as a schema
        # object. Rely on the in-prompt schema plus fence stripping instead.
        accepts_response_format=False,
        honours_seed=False,
        accepts_reasoning_effort=False,
    ),
    "google": VendorQuirks(
        # Gemini reasons by default and its OpenAI shim rejects
        # ``thinking: {"type": "disabled"}``; ``reasoning_effort=none`` is the
        # only knob on the compat surface that turns hidden CoT off.
        reasoning_efforts=("none", "low", "medium", "high"),
        reasoning_disable_effort="none",
    ),
    "deepseek": VendorQuirks(
        supports_embedding=False,
        thinking_flag=True,
        stream_usage_option=True,
        cache_hit_fields=("prompt_cache_hit_tokens",),
    ),
    "zai": VendorQuirks(
        thinking_flag=True,
    ),
}

_DEFAULT = _QUIRKS["openai"]


def quirks_for(api_kind: str | None) -> VendorQuirks:
    """Quirks for one ``api_kind``, defaulting to the OpenAI-compat posture."""
    return _QUIRKS.get(api_kind or "", _DEFAULT)


def known_api_kinds() -> tuple[str, ...]:
    return tuple(_QUIRKS)


def auth_headers(api_kind: str | None, api_key: str | None) -> dict[str, str]:
    """Auth headers for a vendor, empty when no key is configured."""
    if not api_key:
        return {}
    quirks = quirks_for(api_kind)
    if quirks.auth == AUTH_X_API_KEY:
        headers = {"x-api-key": api_key}
    else:
        headers = {"Authorization": f"Bearer {api_key}"}
    headers.update(quirks.auth_extra_headers)
    return headers


def native_root(base_url: str) -> str:
    """Strip an OpenAI-compat suffix so one base_url serves both protocols.

    Users keep a single ``http://host:11434/v1`` and both api_kinds work;
    ``/api/...`` paths replace the compat suffix when present.
    """
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return base[:-3]
    if base.endswith("/api"):
        return base[:-4]
    return base


def chat_url(api_kind: str | None, base_url: str) -> str:
    if quirks_for(api_kind).native_protocol:
        return f"{native_root(base_url)}/api/chat"
    return f"{base_url}/chat/completions"


def embeddings_url(api_kind: str | None, base_url: str) -> str:
    if quirks_for(api_kind).native_protocol:
        return f"{native_root(base_url)}/api/embed"
    return f"{base_url}/embeddings"


@dataclass(frozen=True)
class ProbeTarget:
    url: str
    headers: dict[str, str]
    label: str


def models_probe(
    api_kind: str | None, base_url: str, api_key: str | None = None
) -> ProbeTarget:
    """Where to ask a vendor which models it serves.

    Shared by the setup wizard's model probe and the health check so both
    reach a cloud vendor instead of assuming Ollama's ``/api/tags``.
    """
    if quirks_for(api_kind).native_protocol:
        return ProbeTarget(
            url=f"{native_root(base_url)}/api/tags",
            headers=auth_headers(api_kind, api_key),
            label="ollama_native:/api/tags",
        )
    return ProbeTarget(
        url=f"{base_url.rstrip('/')}/models",
        headers=auth_headers(api_kind, api_key),
        label="openai_compat:/v1/models",
    )


def output_cap_keys(api_kind: str | None) -> tuple[str, ...]:
    """Output-cap param keys, the vendor's canonical one first.

    The same "max output tokens" concept goes by ``max_tokens``,
    ``max_completion_tokens`` or ``num_predict`` depending on the vendor. The
    remaining keys stay in the lookup so a value set under a different
    api_kind still reports rather than silently reading as unset.
    """
    canonical = quirks_for(api_kind).output_cap_key
    rest = tuple(
        key
        for key in ("max_tokens", "max_completion_tokens", "num_predict")
        if key != canonical
    )
    return (canonical, *rest)


def assert_can_embed(api_kind: str | None, model: str) -> None:
    """Reject an embed call against a vendor with no embeddings endpoint.

    Anthropic and DeepSeek expose chat completions only; such a call 404s on
    every request, so fail loud naming the vendor. This is the surviving
    runtime guard — the provider table that carried a ``supports_embedding``
    flag is gone (doc 11 §4).
    """
    if not quirks_for(api_kind).supports_embedding:
        raise RuntimeError(
            f"Vendor {api_kind!r} has no embeddings endpoint; the embedding "
            f"purpose cannot use this provider (model={model!r}). Point the "
            f"embedding purpose at a provider that supports embeddings."
        )


def assert_reasoning_effort(api_kind: str | None, value: object) -> None:
    """Reject a ``reasoning_effort`` the vendor does not accept.

    Sending one is a 400 on every request, so the local failure carries the
    vendor's actual vocabulary instead of the vendor's opaque error.
    """
    if value is None:
        return
    quirks = quirks_for(api_kind)
    if not quirks.accepts_reasoning_effort:
        raise RuntimeError(
            f"Vendor {api_kind!r} accepts no 'reasoning_effort' param; remove "
            f"it from the purpose params."
        )
    if value in quirks.retired_reasoning_efforts:
        raise RuntimeError(
            f"Vendor {api_kind!r} retired reasoning_effort={value!r}; it is no "
            f"longer part of the effort set. Use one of: "
            f"{', '.join(quirks.reasoning_efforts)}."
        )
    if quirks.reasoning_efforts and value not in quirks.reasoning_efforts:
        raise RuntimeError(
            f"Vendor {api_kind!r} does not accept reasoning_effort={value!r}. "
            f"Use one of: {', '.join(quirks.reasoning_efforts)}."
        )

"""Default LLM provider / profile / purpose-config seed data.

Used by the setup wizard to bootstrap a fresh install. NOT seeded by
the migration — the wizard's finalize handler reads these dataclasses,
optionally overrides the rows that match the user's chosen ``api_kind``
(api_key, model per purpose), and then bulk-inserts everything.

Why pure Python instead of an Alembic seed:

- Seeding from migrations forced every fresh install to ship rows
  the operator might never use. Worse, the rows had ``api_key=NULL``
  for cloud vendors, so the orchestrator quietly resolved with no
  Authorization header and returned 401 on the first request.
- Migrations are immutable history; seed data is operational config.
  Mixing them means any change to a default model has to ship as
  another migration. With this in code, defaults are reviewed, diffed,
  and tested like any other source file.
- The wizard wants to *modify* the seed (apply user input) before
  insert. A SQL-only seed cannot be partially overridden — the wizard
  ends up doing UPDATEs on top of fresh INSERTs, which is what the
  pre-refactor code was doing and getting wrong.

Layout:

* ``DEFAULT_PROVIDERS`` — one row per supported vendor, ``api_key=None``.
  A catalogue keyed by ``api_kind``; each ``DEFAULT_PROFILES`` entry
  names one of these rows in its ``provider_name`` field. Not written
  to any table itself — the frontend owns its own base-URL defaults
  (``StepLLM.tsx``'s ``BASE_URL_DEFAULTS``) and does not read this list.
* ``DEFAULT_PROFILES``  — preset bundles of model + params per vendor.
  Naming convention is ``<api_kind>-<tier-?><purpose>`` (e.g.
  ``openai-extraction``, ``deepseek-flash-classification``).
* ``DEFAULT_PURPOSE_CONFIGS`` — one row per pipeline purpose. The
  defaults all point at the local Ollama install so a no-credentials
  fresh install can still run end-to-end against models on the host.
* ``DEFAULT_PROVIDER_ROWS`` — the rows actually written to the
  ``llm_providers`` table, distinct from ``DEFAULT_PROVIDERS`` above.
"""
from __future__ import annotations

import os

# The Ollama endpoint the seeds pin, overridable by environment.
#
# **Localhost is the right product default and the wrong one for this machine.**
# A fresh install has no LAN embedder to find, so the default must stay
# `localhost`. But the embedder this repo actually runs against lives at
# `192.168.0.196:11434` (recorded under "Live model endpoints" in CLAUDE.md),
# and the API e2e suite boots a disposable stack that posts a bare password to
# `/api/v1/setup` — so it gets these seeds verbatim, with no overlay, and
# every embed call went to a localhost Ollama that is not there. That is what
# reduced the v0.5 release's e2e step to a skip whose own message read
# "search cannot be proven without a reachable embedder", green with its
# load-bearing assertion never run.
OLLAMA_BASE_URL = os.getenv("DARKMEM_OLLAMA_BASE_URL", "http://localhost:11434/v1")

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderSeed:
    name: str
    provider: str
    base_url: str
    api_kind: str
    supports_embedding: bool


@dataclass(frozen=True)
class ProfileSeed:
    name: str
    provider_name: str  # references ProviderSeed.name
    model: str
    params: dict[str, Any] = field(default_factory=dict)
    is_embedding: bool = False
    reasoning: bool = False


@dataclass(frozen=True)
class PurposeConfigSeed:
    purpose: str
    provider_name: str  # references ProviderSeed.name
    model: str
    api_kind: str
    base_url: str
    dimensions: int | None = None
    reasoning: bool = False
    params: dict[str, Any] = field(default_factory=dict)


DEFAULT_PROVIDERS: list[ProviderSeed] = [
    ProviderSeed("ollama",    "ollama",    OLLAMA_BASE_URL,                              "ollama",    True),
    ProviderSeed("openai",    "openai",    "https://api.openai.com/v1",                              "openai",    True),
    ProviderSeed("anthropic", "anthropic", "https://api.anthropic.com/v1",                           "anthropic", False),
    ProviderSeed("google",    "google",    "https://generativelanguage.googleapis.com/v1beta/openai", "google",   True),
    ProviderSeed("deepseek",  "deepseek",  "https://api.deepseek.com/v1",                            "deepseek",  False),
    ProviderSeed("zai",       "zai",       "https://api.z.ai/api/paas/v4",                           "zai",       True),
]


@dataclass(frozen=True)
class ProviderRowSeed:
    name: str
    api_kind: str
    base_url: str
    api_key: str | None = None


# The rows actually written to `llm_providers`. DEFAULT_PROVIDERS above stays a
# vendor *catalogue* keyed by api_kind — it is not this list, and conflating
# the two flips the wire protocol: its `ollama` entry is api_kind='ollama'
# (the native /api path) while every purpose below resolves api_kind='openai'
# against a /v1-suffixed URL (the compat path).
#
# `verification-judge` exists so the verification purpose does not share a
# provider by default: two of the judge's six identity fields (base_url,
# api_kind) live on the provider row, so a shared provider would put the
# qualification identity behind an unrelated edit.
DEFAULT_PROVIDER_ROWS: list[ProviderRowSeed] = [
    ProviderRowSeed("ollama-local", "openai", OLLAMA_BASE_URL),
    ProviderRowSeed("verification-judge", "openai", OLLAMA_BASE_URL),
]


DEFAULT_PROFILES: list[ProfileSeed] = [
    # Ollama
    ProfileSeed("ollama-embedding",      "ollama", "qwen3-embedding:0.6b", {},                         is_embedding=True),
    ProfileSeed("ollama-extraction",     "ollama", "qwen2.5:3b",            {"temperature": 0}),
    ProfileSeed("ollama-classification", "ollama", "qwen2.5:3b",            {"temperature": 0}),
    ProfileSeed("ollama-reasoning",      "ollama", "qwen3:4b",              {"temperature": 0.7},      reasoning=True),
    ProfileSeed("ollama-summarization",  "ollama", "qwen2.5:3b",            {"temperature": 0.3}),
    ProfileSeed("ollama-reranker",       "ollama", "qwen2.5:3b",            {"temperature": 0}),
    # OpenAI
    ProfileSeed("openai-embedding",       "openai", "text-embedding-3-small", {},                          is_embedding=True),
    ProfileSeed("openai-embedding-large", "openai", "text-embedding-3-large", {},                          is_embedding=True),
    ProfileSeed("openai-extraction",      "openai", "gpt-5.4-mini",           {"temperature": 1, "reasoning_effort": "none", "verbosity": "low",    "max_completion_tokens": 8192}),
    ProfileSeed("openai-nano-extraction", "openai", "gpt-5.4-nano",           {"temperature": 1, "reasoning_effort": "none", "verbosity": "low",    "max_completion_tokens": 8192}),
    ProfileSeed("openai-classification",  "openai", "gpt-5.4-nano",           {"temperature": 1, "reasoning_effort": "none", "verbosity": "low",    "max_completion_tokens":   64}),
    ProfileSeed("openai-reasoning",       "openai", "gpt-5.4",                {"temperature": 1, "reasoning_effort": "high", "verbosity": "medium", "max_completion_tokens": 4096}, reasoning=True),
    ProfileSeed("openai-summarization",   "openai", "gpt-5.4-mini",           {"temperature": 1, "reasoning_effort": "none", "verbosity": "medium", "max_completion_tokens":  512}),
    ProfileSeed("openai-reranker",        "openai", "gpt-5.4-nano",           {"temperature": 1, "reasoning_effort": "none", "verbosity": "low",    "max_completion_tokens":   32}),
    # z.ai
    ProfileSeed("zai-flash-extraction",     "zai", "glm-4.7-flash", {"temperature": 0,   "max_tokens": 8192}),
    ProfileSeed("zai-flash-classification", "zai", "glm-4.5-flash", {"temperature": 0,   "max_tokens":   64}),
    ProfileSeed("zai-flash-summarization",  "zai", "glm-4.5-flash", {"temperature": 0.3, "max_tokens":  512}),
    ProfileSeed("zai-flash-reranker",       "zai", "glm-4.5-flash", {"temperature": 0,   "max_tokens":   32}),
    ProfileSeed("zai-turbo-extraction",     "zai", "glm-5-turbo",   {"temperature": 0,   "max_tokens": 8192}),
    ProfileSeed("zai-turbo-classification", "zai", "glm-5-turbo",   {"temperature": 0,   "max_tokens":   64}),
    ProfileSeed("zai-turbo-summarization",  "zai", "glm-5-turbo",   {"temperature": 0.3, "max_tokens":  512}),
    ProfileSeed("zai-turbo-reranker",       "zai", "glm-5-turbo",   {"temperature": 0,   "max_tokens":   32}),
    ProfileSeed("zai-turbo-reasoning",      "zai", "glm-5-turbo",   {"temperature": 0.7, "max_tokens": 4096}, reasoning=True),
    # DeepSeek
    ProfileSeed("deepseek-flash-extraction",     "deepseek", "deepseek-v4-flash", {"temperature": 0,   "max_tokens": 8192, "thinking": {"type": "disabled"}}),
    ProfileSeed("deepseek-pro-extraction",       "deepseek", "deepseek-v4-pro",   {"temperature": 0,   "max_tokens": 8192, "thinking": {"type": "disabled"}}),
    ProfileSeed("deepseek-flash-classification", "deepseek", "deepseek-chat",     {"temperature": 0,   "max_tokens":   64}),
    ProfileSeed("deepseek-flash-summarization",  "deepseek", "deepseek-chat",     {"temperature": 0.3, "max_tokens":  512}),
    ProfileSeed("deepseek-flash-reranker",       "deepseek", "deepseek-chat",     {"temperature": 0,   "max_tokens":   32}),
    ProfileSeed("deepseek-flash-reasoning",      "deepseek", "deepseek-reasoner", {"temperature": 0.7, "max_tokens": 4096}, reasoning=True),
    ProfileSeed("deepseek-pro-reasoning",        "deepseek", "deepseek-v4-pro",   {"temperature": 0.7, "max_tokens": 4096}, reasoning=True),
    # Anthropic
    ProfileSeed("anthropic-haiku-extraction",     "anthropic", "claude-haiku-4-5",  {"temperature": 0,   "max_tokens": 8192}),
    ProfileSeed("anthropic-sonnet-extraction",    "anthropic", "claude-sonnet-4-6", {"temperature": 0,   "max_tokens": 8192}),
    ProfileSeed("anthropic-haiku-classification", "anthropic", "claude-haiku-4-5",  {"temperature": 0,   "max_tokens":   64}),
    ProfileSeed("anthropic-haiku-summarization",  "anthropic", "claude-haiku-4-5",  {"temperature": 0.3, "max_tokens":  512}),
    ProfileSeed("anthropic-haiku-reranker",       "anthropic", "claude-haiku-4-5",  {"temperature": 0,   "max_tokens":   32}),
    ProfileSeed("anthropic-sonnet-reasoning",     "anthropic", "claude-sonnet-4-6", {"temperature": 0.7, "max_tokens": 4096}, reasoning=True),
    # Google
    ProfileSeed("google-embedding",          "google", "gemini-embedding-001",  {},                                                                          is_embedding=True),
    ProfileSeed("google-lite-extraction",    "google", "gemini-2.5-flash-lite", {"temperature": 0,   "max_tokens": 8192, "reasoning_effort": "none"}),
    ProfileSeed("google-flash-extraction",   "google", "gemini-2.5-flash",      {"temperature": 0,   "max_tokens": 8192, "reasoning_effort": "none"}),
    ProfileSeed("google-flash-classification","google", "gemini-2.5-flash",     {"temperature": 0,   "max_tokens":   64, "reasoning_effort": "none"}),
    ProfileSeed("google-flash-summarization", "google", "gemini-2.5-flash",     {"temperature": 0.3, "max_tokens":  512, "reasoning_effort": "none"}),
    ProfileSeed("google-flash-reranker",      "google", "gemini-2.5-flash",     {"temperature": 0,   "max_tokens":   32, "reasoning_effort": "none"}),
    ProfileSeed("google-pro-extraction",      "google", "gemini-2.5-pro",       {"temperature": 0,   "max_tokens": 8192, "reasoning_effort": "none"}),
    ProfileSeed("google-pro-reasoning",       "google", "gemini-2.5-pro",       {"temperature": 0.7, "max_tokens": 4096, "reasoning_effort": "high"}, reasoning=True),
]




# Default purpose configs: all six purposes pinned to the local Ollama
# install so a fresh deploy with no cloud credentials still runs the
# pipeline end-to-end. The wizard's finalize handler overlays user
# choices on top of these for whichever purposes the user filled in.
DEFAULT_PURPOSE_CONFIGS: list[PurposeConfigSeed] = [
    PurposeConfigSeed("embedding",      "ollama", "qwen3-embedding:0.6b", "openai", OLLAMA_BASE_URL, dimensions=1024, params={}),
    PurposeConfigSeed("extraction",     "ollama", "qwen2.5:3b",           "openai", OLLAMA_BASE_URL, params={"temperature": 0}),
    PurposeConfigSeed("classification", "ollama", "qwen2.5:3b",           "openai", OLLAMA_BASE_URL, params={"temperature": 0}),
    PurposeConfigSeed("reasoning",      "ollama", "qwen2.5:3b",           "openai", OLLAMA_BASE_URL, params={"temperature": 0.7}),
    PurposeConfigSeed("summarization",  "ollama", "qwen2.5:3b",           "openai", OLLAMA_BASE_URL, params={"temperature": 0.3}),
    PurposeConfigSeed("reranker",       "ollama", "qwen2.5:3b",           "openai", OLLAMA_BASE_URL, params={"temperature": 0}),
    # Inert (T1.05, doc 11 §6): seeded and resolvable, dispatched by nothing.
    # First writers are T3.02 (synthesis) and T2.26 (verification).
    PurposeConfigSeed("synthesis",      "ollama", "qwen2.5:3b",           "openai", OLLAMA_BASE_URL, params={"temperature": 0.3}),
    PurposeConfigSeed("verification",   "ollama", "qwen2.5:3b",           "openai", OLLAMA_BASE_URL, params={"temperature": 0}),
]


def default_provider_row_name_for_purpose(purpose: str) -> str:
    """The `llm_providers.name` a default-seeded purpose row references.

    Lives here, not at the call site, so the literal purpose name stays
    inside this module's allowlisted quoted-token exemption (doc 17 §6's
    single-door scan) instead of leaking a second quoted "verification"
    outside the judge module.
    """
    return "verification-judge" if purpose == "verification" else "ollama-local"

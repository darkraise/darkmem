from typing import Literal

from pydantic import BaseModel, Field

from app.config import LLMApiKind


class LLMPurposeConfigSchema(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool = False
    api_kind: LLMApiKind = "openai"
    params: dict = Field(default_factory=dict)
    provider_ref: str | None = None
    profile_ref: str | None = None


class LLMPurposeConfigUpdate(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool | None = None
    api_kind: LLMApiKind | None = None
    params: dict | None = None
    # Empty string clears the reference; absent leaves it untouched.
    provider_ref: str | None = None
    profile_ref: str | None = None


class LLMProviderProfileSchema(BaseModel):
    """One stored provider profile. ``api_key`` is masked with ``"***"``
    on read and accepts the same sentinel on write to mean "leave as is"."""

    provider: str = "openai"
    base_url: str
    api_key: str | None = None
    api_kind: LLMApiKind = "openai"
    supports_embedding: bool = True


class LLMProviderTestRequest(BaseModel):
    """Optional model override for the connectivity probe. ``mode`` selects
    whether the probe hits ``/chat/completions`` (default) or ``/embeddings``
    so the UI can verify both paths against vendors that support both."""

    mode: Literal["chat", "embedding"] = "chat"
    model: str | None = None


class LLMProviderTestResponse(BaseModel):
    ok: bool
    status_code: int | None = None
    latency_ms: int = 0
    url: str = ""
    message: str = ""


class LLMProvidersResponse(BaseModel):
    """All saved profiles, keyed by name. Names are user-chosen labels."""

    profiles: dict[str, LLMProviderProfileSchema] = Field(default_factory=dict)


class LLMProvidersUpdate(BaseModel):
    """Whole-document write of the profile set.

    The endpoint replaces the stored map with what's posted, so the
    handler has to merge the ``"***"`` sentinel back to the existing key
    before persisting.
    """

    profiles: dict[str, LLMProviderProfileSchema]


class LLMProfileSchema(BaseModel):
    """One stored LLM profile (preset bundle of provider + model + defaults)."""

    provider_ref: str
    model: str
    params: dict = Field(default_factory=dict)
    is_embedding: bool = False
    reasoning: bool = False


class LLMProfilesResponse(BaseModel):
    profiles: dict[str, LLMProfileSchema] = Field(default_factory=dict)


class LLMProfilesUpdate(BaseModel):
    profiles: dict[str, LLMProfileSchema]


class LLMProviderModelsResponse(BaseModel):
    """Models the configured Provider exposes, used by the UI to populate
    a model-selection dropdown after the user picks a Provider."""

    models: list[str] = Field(default_factory=list)
    fetched_via: str = ""  # e.g. "openai_compat:/v1/models" or "ollama_native:/api/tags"
    error: str | None = None


class LLMConfigResponse(BaseModel):
    embedding: LLMPurposeConfigSchema
    extraction: LLMPurposeConfigSchema
    classification: LLMPurposeConfigSchema
    reasoning: LLMPurposeConfigSchema
    summarization: LLMPurposeConfigSchema
    reranker: LLMPurposeConfigSchema


class LLMConfigUpdateResponse(LLMConfigResponse):
    """Returned by POST /api/v1/config/llm. Extends LLMConfigResponse with
    computed obsolete counts for the new embedding model."""
    obsolete_after_change: dict[str, int] | None = None


class LLMConfigUpdate(BaseModel):
    embedding: LLMPurposeConfigUpdate | None = None
    extraction: LLMPurposeConfigUpdate | None = None
    classification: LLMPurposeConfigUpdate | None = None
    reasoning: LLMPurposeConfigUpdate | None = None
    summarization: LLMPurposeConfigUpdate | None = None
    reranker: LLMPurposeConfigUpdate | None = None


class StatsResponse(BaseModel):
    memories: int
    tags: int
    entities: int | None = None
    relationships: int | None = None
    sources: list[str] = []

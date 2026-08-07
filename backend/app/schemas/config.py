from pydantic import BaseModel, Field

from app.config import LLMApiKind


class LLMPurposeConfigSchema(BaseModel):
    base_url: str
    model: str
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool = False
    api_kind: LLMApiKind = "openai"
    params: dict = Field(default_factory=dict)
    # Inert: the provider/profile indirection is gone (doc 04 §7). Kept on
    # the wire so the response shape the frontend reads is unchanged by
    # this task; retiring them is the contract task's call.
    provider_ref: str | None = None
    profile_ref: str | None = None
    ml_profile_ref: str | None = None


class LLMPurposeConfigUpdate(BaseModel):
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
    ml_profile_ref: str | None = None


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
    # T2.104: `app.services.config.PURPOSES` has always resolved eight
    # purposes and both `/config/llm` routes have always built a payload
    # keyed on all eight (`{p: cfg_to_schema(c) for p, c in config.items()}`)
    # — this model declared only six, so pydantic's default extra="ignore"
    # silently dropped these two. `verification` is live: doc 04 §8's judge
    # service resolves and dispatches on it since T2.26. `synthesis` stays
    # seeded inert (first consumer T3.02). Read-only here: the request-side
    # `LLMConfigUpdate` below still declares only six, so a write to either
    # purpose through this route is a separate, undecided wire-contract
    # change (see the task's report).
    synthesis: LLMPurposeConfigSchema
    verification: LLMPurposeConfigSchema


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

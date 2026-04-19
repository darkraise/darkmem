from pydantic import BaseModel, Field


class LLMPurposeConfigSchema(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool = False
    tool_call_mode: str = "json"
    params: dict = Field(default_factory=dict)


class LLMPurposeConfigUpdate(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool | None = None
    tool_call_mode: str | None = None
    params: dict | None = None


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

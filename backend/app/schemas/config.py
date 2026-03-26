from pydantic import BaseModel, Field


class LLMPurposeConfigSchema(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    dimensions: int | None = None
    params: dict = Field(default_factory=dict)


class LLMPurposeConfigUpdate(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    dimensions: int | None = None
    params: dict | None = None


class LLMConfigResponse(BaseModel):
    embedding: LLMPurposeConfigSchema
    extraction: LLMPurposeConfigSchema
    reasoning: LLMPurposeConfigSchema
    summarization: LLMPurposeConfigSchema


class LLMConfigUpdate(BaseModel):
    embedding: LLMPurposeConfigUpdate | None = None
    extraction: LLMPurposeConfigUpdate | None = None
    reasoning: LLMPurposeConfigUpdate | None = None
    summarization: LLMPurposeConfigUpdate | None = None


class StatsResponse(BaseModel):
    memories: int
    tags: int
    entities: int | None = None
    relationships: int | None = None
    sources: list[str] = []

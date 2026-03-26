from pydantic import BaseModel, Field


class LLMPurposeConfigSchema(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    dimensions: int | None = None
    params: dict = Field(default_factory=dict)


class LLMConfigResponse(BaseModel):
    embedding: LLMPurposeConfigSchema
    extraction: LLMPurposeConfigSchema
    reasoning: LLMPurposeConfigSchema
    summarization: LLMPurposeConfigSchema


class StatsResponse(BaseModel):
    memories: int
    tags: int
    entities: int | None = None
    relationships: int | None = None
    sources: list[str] = []

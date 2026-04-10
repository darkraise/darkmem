from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PipelineFailureResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    pipeline_name: str
    failed_step: str
    error_message: str | None
    attempts: int
    first_failed_at: datetime
    last_attempt_at: datetime
    resolved_at: datetime | None
    metadata: dict = Field(default_factory=dict)
    entity_preview: str | None = None


class PipelineFailureListResponse(BaseModel):
    items: list[PipelineFailureResponse]
    total: int

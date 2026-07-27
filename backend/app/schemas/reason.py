from pydantic import BaseModel, Field


class ReasonRequest(BaseModel):
    question: str
    limit: int = Field(default=10, ge=1, le=200)
    project: str | None = None


class ReasonResponse(BaseModel):
    answer: str
    sources: list[dict]

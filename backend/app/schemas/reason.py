from pydantic import BaseModel


class ReasonRequest(BaseModel):
    question: str
    limit: int = 10


class ReasonResponse(BaseModel):
    answer: str
    sources: list[dict]

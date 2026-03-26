from pydantic import BaseModel


class TagResponse(BaseModel):
    id: int
    name: str
    category: str | None
    memory_count: int = 0

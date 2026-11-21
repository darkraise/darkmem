import json
from typing import TypedDict

from pydantic import BaseModel, field_validator


class EntityResponse(BaseModel):
    id: str | None
    name: str
    entity_type: str
    properties: dict = {}
    memory_ids: list[str] = []

    @field_validator("properties", mode="before")
    @classmethod
    def parse_properties(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {}
        return v or {}


class RelationResponse(BaseModel):
    type: str | None
    weight: float | None
    source: str | None
    target: str | None


class NeighborsResponse(BaseModel):
    entity: EntityResponse | None
    neighbors: list[EntityResponse]
    relations: list[RelationResponse]


class FullGraphResponse(BaseModel):
    entities: list[EntityResponse]
    relations: list[RelationResponse]


class GraphMemoryNode(TypedDict):
    """One memory node of ``GET /graph/unified``; ``content`` is a preview."""

    id: str
    content: str
    content_truncated: bool
    source: str
    tags: list[str]
    memory_type: str | None
    importance: float
    cluster: int
    project: str | None
    status: str | None

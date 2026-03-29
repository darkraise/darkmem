import json

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

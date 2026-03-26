from pydantic import BaseModel


class EntityResponse(BaseModel):
    id: str | None
    name: str
    entity_type: str
    properties: dict = {}
    memory_ids: list[str] = []


class RelationResponse(BaseModel):
    type: str | None
    weight: float | None
    source: str | None
    target: str | None


class NeighborsResponse(BaseModel):
    entity: EntityResponse | None
    neighbors: list[EntityResponse]
    relations: list[RelationResponse]

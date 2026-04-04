from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.models.memory import Memory, Tag


class MemoryRepositoryBase(ABC):
    @abstractmethod
    async def create(self, content: str, source: str, source_agent: str | None, memory_type: str | None, importance: float, metadata: dict, expires_at=None) -> Memory: ...

    @abstractmethod
    async def get(self, memory_id: UUID) -> Memory | None: ...

    @abstractmethod
    async def update(self, memory_id: UUID, **fields) -> Memory | None: ...

    @abstractmethod
    async def delete(self, memory_id: UUID) -> bool: ...

    @abstractmethod
    async def list_memories(self, offset: int = 0, limit: int = 50, is_archived: bool = False) -> tuple[list[Memory], int]: ...

    @abstractmethod
    async def search_by_tags(self, query: str | None = None, tags_any: list[str] | None = None, tags_all: list[str] | None = None, memory_type: str | None = None, source: str | None = None, limit: int = 20) -> list[Memory]: ...

    @abstractmethod
    async def set_tags(self, memory_id: UUID, tag_names: list[str]) -> None: ...


class TagRepositoryBase(ABC):
    @abstractmethod
    async def get_or_create(self, name: str, category: str | None = None) -> Tag: ...

    @abstractmethod
    async def list_all(self) -> list[Tag]: ...

    @abstractmethod
    async def get_with_counts(self) -> list[tuple[Tag, int]]: ...


class AuditRepositoryBase(ABC):
    @abstractmethod
    async def log(self, action: str, memory_id: UUID | None = None, api_key_id: UUID | None = None, details: dict | None = None) -> None: ...

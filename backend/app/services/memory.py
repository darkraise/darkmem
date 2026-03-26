from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.repositories.relational import PostgresAuditRepository, PostgresMemoryRepository
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate


class MemoryService:
    def __init__(self, session: AsyncSession):
        self.memory_repo = PostgresMemoryRepository(session)
        self.audit_repo = PostgresAuditRepository(session)
        self.session = session

    async def create_memory(self, data: MemoryCreate, api_key_id: UUID | None) -> Memory:
        memory = await self.memory_repo.create(
            content=data.content,
            source=data.source,
            source_agent=data.source_agent,
            memory_type=data.memory_type,
            importance=data.importance,
            metadata=data.metadata,
            expires_at=data.expires_at,
        )

        if data.tags:
            await self.memory_repo.set_tags(memory.id, data.tags)
            await self.session.refresh(memory, ["tags"])

        await self.audit_repo.log("create", memory.id, api_key_id, {"source": data.source})
        return memory

    async def get_memory(self, memory_id: UUID) -> Memory | None:
        return await self.memory_repo.get(memory_id)

    async def update_memory(self, memory_id: UUID, data: MemoryUpdate, api_key_id: UUID | None) -> Memory | None:
        update_fields = data.model_dump(exclude_unset=True, exclude={"tags"})
        memory = await self.memory_repo.update(memory_id, **update_fields)
        if not memory:
            return None

        if data.tags is not None:
            await self.memory_repo.set_tags(memory_id, data.tags)
            await self.session.refresh(memory, ["tags"])

        await self.audit_repo.log("update", memory_id, api_key_id, {"fields": list(update_fields.keys())})
        return memory

    async def delete_memory(self, memory_id: UUID, api_key_id: UUID | None) -> bool:
        result = await self.memory_repo.delete(memory_id)
        if result:
            await self.audit_repo.log("delete", memory_id, api_key_id, {})
        return result

    async def search_memories(self, params: MemorySearchRequest) -> list[Memory]:
        return await self.memory_repo.search_by_tags(
            query=params.query,
            tags_any=params.tags_any,
            tags_all=params.tags_all,
            memory_type=params.memory_type,
            source=params.source,
            limit=params.limit,
        )

    async def list_memories(self, offset: int = 0, limit: int = 50) -> tuple[list[Memory], int]:
        return await self.memory_repo.list_memories(offset=offset, limit=limit)

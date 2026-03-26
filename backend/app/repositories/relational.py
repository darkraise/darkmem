from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.api_key import ApiKey
from app.models.audit import AuditLog
from app.models.memory import Memory, Tag, memory_tags

from .base import ApiKeyRepositoryBase, AuditRepositoryBase, MemoryRepositoryBase, TagRepositoryBase


class PostgresMemoryRepository(MemoryRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, content, source, source_agent, memory_type, importance, metadata, expires_at=None):
        memory = Memory(
            content=content,
            source=source,
            source_agent=source_agent,
            memory_type=memory_type,
            importance=importance,
            metadata_=metadata,
            expires_at=expires_at,
        )
        self.session.add(memory)
        await self.session.flush()
        await self.session.refresh(memory, ["tags"])
        return memory

    async def get(self, memory_id):
        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.id == memory_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, memory_id, **fields):
        memory = await self.get(memory_id)
        if not memory:
            return None
        for key, value in fields.items():
            if key == "metadata":
                setattr(memory, "metadata_", value)
            elif hasattr(memory, key):
                setattr(memory, key, value)
        await self.session.flush()
        await self.session.refresh(memory, ["tags"])
        return memory

    async def delete(self, memory_id):
        memory = await self.get(memory_id)
        if not memory:
            return False
        await self.session.delete(memory)
        await self.session.flush()
        return True

    async def list_memories(self, offset=0, limit=50, is_archived=False):
        count_stmt = select(func.count()).select_from(Memory).where(Memory.is_archived == is_archived)
        total = (await self.session.execute(count_stmt)).scalar()

        stmt = (
            select(Memory)
            .options(selectinload(Memory.tags))
            .where(Memory.is_archived == is_archived)
            .order_by(Memory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def search_by_tags(self, query=None, tags_any=None, tags_all=None, memory_type=None, source=None, limit=20):
        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712

        if query:
            stmt = stmt.where(Memory.content.ilike(f"%{query}%"))

        if tags_any:
            stmt = stmt.where(Memory.tags.any(Tag.name.in_(tags_any)))

        if tags_all:
            for tag_name in tags_all:
                stmt = stmt.where(Memory.tags.any(Tag.name == tag_name))

        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)

        if source:
            stmt = stmt.where(Memory.source == source)

        stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_tags(self, memory_id, tag_names):
        memory = await self.get(memory_id)
        if not memory:
            return

        tags = []
        for name in tag_names:
            category = name.split("/")[0] if "/" in name else None
            result = await self.session.execute(select(Tag).where(Tag.name == name))
            tag = result.scalar_one_or_none()
            if not tag:
                tag = Tag(name=name, category=category)
                self.session.add(tag)
                await self.session.flush()
            tags.append(tag)

        memory.tags = tags
        await self.session.flush()


class PostgresTagRepository(TagRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, name, category=None):
        if category is None and "/" in name:
            category = name.split("/")[0]

        result = await self.session.execute(select(Tag).where(Tag.name == name))
        tag = result.scalar_one_or_none()

        if not tag:
            tag = Tag(name=name, category=category)
            self.session.add(tag)
            await self.session.flush()

        return tag

    async def list_all(self):
        result = await self.session.execute(select(Tag).order_by(Tag.name))
        return list(result.scalars().all())

    async def get_with_counts(self):
        stmt = (
            select(Tag, func.count(memory_tags.c.memory_id).label("count"))
            .outerjoin(memory_tags)
            .group_by(Tag.id)
            .order_by(Tag.name)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]


class PostgresApiKeyRepository(ApiKeyRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name, key_hash, scopes, profile, expires_at=None):
        api_key = ApiKey(name=name, key_hash=key_hash, scopes=scopes, profile=profile, expires_at=expires_at)
        self.session.add(api_key)
        await self.session.flush()
        return api_key

    async def get_by_key_hash(self, key_hash):
        result = await self.session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
        return result.scalar_one_or_none()

    async def list_all(self):
        result = await self.session.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
        return list(result.scalars().all())

    async def delete(self, key_id):
        result = await self.session.execute(select(ApiKey).where(ApiKey.id == key_id))
        key = result.scalar_one_or_none()
        if not key:
            return False
        await self.session.delete(key)
        await self.session.flush()
        return True

    async def update_last_used(self, key_id):
        result = await self.session.execute(select(ApiKey).where(ApiKey.id == key_id))
        key = result.scalar_one_or_none()
        if key:
            key.last_used_at = datetime.now(timezone.utc)
            await self.session.flush()


class PostgresAuditRepository(AuditRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, action, memory_id=None, api_key_id=None, details=None):
        entry = AuditLog(action=action, memory_id=memory_id, api_key_id=api_key_id, details=details or {})
        self.session.add(entry)
        await self.session.flush()

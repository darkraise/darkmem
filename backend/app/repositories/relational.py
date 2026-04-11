from uuid import UUID

from sqlalchemy import func, select, text as sa_text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditLog
from app.models.memory import Memory, Tag, memory_tags

from .base import AuditRepositoryBase, MemoryRepositoryBase, TagRepositoryBase


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

    async def get_many(self, memory_ids: list) -> list[Memory]:
        if not memory_ids:
            return []
        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.id.in_(memory_ids))
        result = await self.session.execute(stmt)
        by_id = {m.id: m for m in result.scalars().all()}
        return [by_id[mid] for mid in memory_ids if mid in by_id]

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
        await self.session.refresh(memory)
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

    async def search_by_tags(self, query=None, tags_any=None, tags_all=None, memory_type=None, source=None, wing=None, room=None, hall=None, limit=20):
        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712

        if query:
            stmt = stmt.where(
                sa_text("memories.search_vector @@ plainto_tsquery('english', :fts_query)").bindparams(fts_query=query)
            )

        if tags_any:
            stmt = stmt.where(Memory.tags.any(Tag.name.in_(tags_any)))

        if tags_all:
            for tag_name in tags_all:
                stmt = stmt.where(Memory.tags.any(Tag.name == tag_name))

        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)

        if source:
            stmt = stmt.where(Memory.source == source)

        if wing is not None:
            stmt = stmt.where(Memory.wing == wing)

        if room is not None:
            stmt = stmt.where(Memory.room == room)

        if hall is not None:
            stmt = stmt.where(Memory.hall == hall)

        stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_tags_paginated(self, query=None, tags_any=None, tags_all=None, memory_type=None, source=None, wing=None, room=None, hall=None, limit=20, offset=0):
        base = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712

        if query:
            base = base.where(
                sa_text("memories.search_vector @@ plainto_tsquery('english', :fts_query)").bindparams(fts_query=query)
            )
        if tags_any:
            base = base.where(Memory.tags.any(Tag.name.in_(tags_any)))
        if tags_all:
            for tag_name in tags_all:
                base = base.where(Memory.tags.any(Tag.name == tag_name))
        if memory_type:
            base = base.where(Memory.memory_type == memory_type)
        if source:
            base = base.where(Memory.source == source)
        if wing is not None:
            base = base.where(Memory.wing == wing)
        if room is not None:
            base = base.where(Memory.room == room)
        if hall is not None:
            base = base.where(Memory.hall == hall)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        items_stmt = base.order_by(Memory.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(items_stmt)
        return list(result.scalars().all()), total

    async def get_palace_room_data(self) -> list[dict]:
        result = await self.session.execute(
            sa_text("""
                SELECT room, wing, hall, created_at::date AS date
                FROM memories
                WHERE room IS NOT NULL
                  AND room <> 'general'
                  AND wing IS NOT NULL
                ORDER BY created_at
            """)
        )
        return [dict(r) for r in result.mappings()]

    async def set_tags(self, memory_id, tag_names):
        memory = await self.get(memory_id)
        if not memory:
            return
        if not tag_names:
            memory.tags = []
            await self.session.flush()
            return

        for name in tag_names:
            category = name.split("/")[0] if "/" in name else None
            await self.session.execute(
                insert(Tag)
                .values(name=name, category=category)
                .on_conflict_do_nothing(index_elements=["name"])
            )
        await self.session.flush()
        result = await self.session.execute(select(Tag).where(Tag.name.in_(tag_names)))
        memory.tags = list(result.scalars().all())
        await self.session.flush()


class PostgresTagRepository(TagRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, name, category=None):
        if category is None and "/" in name:
            category = name.split("/")[0]

        await self.session.execute(
            insert(Tag)
            .values(name=name, category=category)
            .on_conflict_do_nothing(index_elements=["name"])
        )
        await self.session.flush()
        result = await self.session.execute(select(Tag).where(Tag.name == name))
        return result.scalar_one()

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


class PostgresAuditRepository(AuditRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, action, memory_id=None, api_key_id=None, details=None):
        entry = AuditLog(action=action, memory_id=memory_id, api_key_id=api_key_id, details=details or {})
        self.session.add(entry)
        await self.session.flush()

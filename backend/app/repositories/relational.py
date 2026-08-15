from uuid import UUID

from sqlalchemy import func, select, text as sa_text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.memory import Memory, Tag, memory_tags, tag_category
from app.services.events import record_event

from .base import AuditRepositoryBase, MemoryRepositoryBase, TagRepositoryBase

# One supersession write can flip many same-project candidates at once
# (`detect_supersessions` has no per-write cap), and the memory-detail page
# renders predecessors inline, never paginated — so the reverse lookup is
# bounded rather than open-ended.
MEMORY_PREDECESSORS_LIMIT = 20


def predecessors_stmt(memory_id, limit: int = MEMORY_PREDECESSORS_LIMIT):
    """The reverse-lineage query, factored out so the EXPLAIN test in
    `tests/test_memory_lineage_index.py` proves the plan of the statement
    that actually runs rather than a hand-copied lookalike."""
    return (
        select(Memory)
        .where(Memory.superseded_by == memory_id)
        .order_by(Memory.created_at.desc())
        .limit(limit)
    )


class PostgresMemoryRepository(MemoryRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, content, source, source_agent, memory_type, importance, metadata, expires_at=None, project=None, origin_key=None):
        kwargs = dict(
            content=content,
            source=source,
            source_agent=source_agent,
            memory_type=memory_type,
            importance=importance,
            metadata_=metadata,
            expires_at=expires_at,
            origin_key=origin_key,
        )
        if project is not None:
            kwargs["project"] = project
        memory = Memory(**kwargs)
        self.session.add(memory)
        await self.session.flush()
        await self.session.refresh(memory, ["tags"])
        return memory

    async def get(self, memory_id):
        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.id == memory_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_predecessors(self, memory_id, limit: int = MEMORY_PREDECESSORS_LIMIT) -> list[Memory]:
        """Memories this one directly superseded — the reverse of `superseded_by`.

        Backed by `ix_memories_superseded_by` (T1.66); see
        `tests/test_memory_lineage_index.py` for the EXPLAIN proof that the
        planner actually uses it.
        """
        result = await self.session.execute(predecessors_stmt(memory_id, limit))
        return list(result.scalars().all())

    async def get_many(self, memory_ids: list) -> list[Memory]:
        if not memory_ids:
            return []
        normalized = [UUID(m) if isinstance(m, str) else m for m in memory_ids]
        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.id.in_(normalized))
        result = await self.session.execute(stmt)
        by_id = {m.id: m for m in result.scalars().all()}
        return [by_id[mid] for mid in normalized if mid in by_id]

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
        # Full refresh loads server-side columns (e.g. updated_at) so later
        # attribute access during response serialization doesn't trigger a lazy
        # load outside the async greenlet (MissingGreenlet); the second refresh
        # reloads the tags relationship.
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

    def _apply_filters(
        self,
        stmt,
        query=None,
        tags_any=None,
        tags_all=None,
        memory_type=None,
        source=None,
        project=None,
        status=None,
        technologies_any=None,
        source_any=None,
        memory_type_any=None,
    ):
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
        if memory_type_any:
            stmt = stmt.where(Memory.memory_type.in_(list(memory_type_any)))
        if source:
            stmt = stmt.where(Memory.source == source)
        if source_any:
            stmt = stmt.where(Memory.source.in_(list(source_any)))
        if project is not None:
            stmt = stmt.where(Memory.project == project)
        if status:
            stmt = stmt.where(Memory.status.in_(status))
        if technologies_any:
            stmt = stmt.where(Memory.technologies.overlap(list(technologies_any)))
        return stmt

    async def search_by_tags(self, query=None, tags_any=None, tags_all=None, memory_type=None, source=None, limit=20, project=None, status=None, technologies_any=None, source_any=None, memory_type_any=None):
        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712
        stmt = self._apply_filters(
            stmt,
            query=query, tags_any=tags_any, tags_all=tags_all,
            memory_type=memory_type, source=source,
            project=project, status=status, technologies_any=technologies_any,
            source_any=source_any, memory_type_any=memory_type_any,
        )
        stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_tags_paginated(self, query=None, tags_any=None, tags_all=None, memory_type=None, source=None, limit=20, offset=0, project=None, status=None, technologies_any=None, source_any=None, memory_type_any=None):
        base = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712
        base = self._apply_filters(
            base,
            query=query, tags_any=tags_any, tags_all=tags_all,
            memory_type=memory_type, source=source,
            project=project, status=status, technologies_any=technologies_any,
            source_any=source_any, memory_type_any=memory_type_any,
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        items_stmt = base.order_by(Memory.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(items_stmt)
        return list(result.scalars().all()), total

    async def set_tags(self, memory_id, tag_names):
        memory = await self.get(memory_id)
        if not memory:
            return
        if not tag_names:
            memory.tags = []
            await self.session.flush()
            return

        # ``on_conflict_do_nothing`` upserts the tag rows but returns nothing for
        # the rows that already existed, so we cannot read the Tag instances back
        # from the INSERT. Re-select by name after the flush to get the full set
        # (newly-inserted + pre-existing) as managed ORM objects, then assign the
        # relationship. The ``Tag.memories`` side is ``lazy='noload'`` (see the
        # model), so this assignment writes only the ``memory_tags`` link rows and
        # never triggers a back-populate load of every memory carrying each tag.
        for name in tag_names:
            category = tag_category(name)
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
        if category is None:
            category = tag_category(name)

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

    async def prune_orphans(self) -> int:
        """Delete tags no memory references any more, returning the count.

        Tags are auto-created from memory tag strings and linked only through
        ``memory_tags`` (ON DELETE CASCADE). Deleting a memory drops the link
        rows but leaves the tag row behind, so the ``tags`` table — and every
        count derived from it (dashboard stat, tag filter dropdown) — keeps
        showing tags that no live memory carries. Mirrors
        ``PostgresGraphRepository.prune_orphan_entities`` for the graph."""
        result = await self.session.execute(
            sa_text("""
                DELETE FROM tags t
                WHERE NOT EXISTS (
                    SELECT 1 FROM memory_tags mt WHERE mt.tag_id = t.id
                )
                RETURNING t.id
            """)
        )
        return len(result.scalars().all())


class PostgresAuditRepository(AuditRepositoryBase):
    # Only the two actions T1.07 names (capture, pipeline outcome) are
    # remapped onto doc 04 §8.1's closed vocabulary. "update"/"delete"/
    # "merge" are unchanged: they are not among the four subsystems T1.07
    # scopes (capture, extraction, supersession, pipeline outcomes), and
    # ``test_audit_endpoint.py`` already asserts the exact strings the
    # audit endpoint's action filter excludes.
    _ACTION_EVENT_TYPE = {
        "create": "created",
        "pipeline": "extracted",
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, action, memory_id=None, api_key_id=None, details=None, *, actor=None):
        await record_event(
            self.session,
            event_type=self._ACTION_EVENT_TYPE.get(action, action),
            object_type="memory" if memory_id else "system",
            object_id=memory_id,
            actor=actor,
            api_key_id=api_key_id,
            payload=details or {},
        )

import uuid
from datetime import datetime

from sqlalchemy import REAL, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.utils.ids import new_id

from .base import Base


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    memory_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    # Inert until T2.27 (the code deriver). A repo id here is the code-side
    # analog of a memory id: it lets code assert a graph row without a memory.
    repo_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("name", "entity_type"),)


class EntityRelation(Base):
    __tablename__ = "entity_relations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False,
    )
    rel_type: Mapped[str] = mapped_column(String(100), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    weight: Mapped[float] = mapped_column(Float, default=0.5)
    memory_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    # Inert until T2.27 — see Entity.repo_ids.
    repo_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source_entity_id", "target_entity_id", "rel_type"),
    )


class KnowledgeTriple(Base):
    __tablename__ = "knowledge_triples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    # Soft references, deliberately without ForeignKey (doc 04 §8.3): the
    # graph side deletes entities aggressively, but this table's contract is
    # invalidate-not-delete, so an expired triple must survive its endpoints.
    # subject_name / object_name carry the durable identity instead.
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    subject_name: Mapped[str] = mapped_column(Text, nullable=False)
    object_name: Mapped[str] = mapped_column(Text, nullable=False)
    rel_type: Mapped[str] = mapped_column(Text, nullable=False)
    valid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reference_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    project: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")
    triple_key: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="candidate")
    confidence: Mapped[float | None] = mapped_column(REAL)
    applies_when: Mapped[dict | None] = mapped_column(JSONB)
    learned_in: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    review_state: Mapped[str | None] = mapped_column(Text)
    source_file: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

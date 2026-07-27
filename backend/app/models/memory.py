import uuid
from datetime import datetime

from typing import Optional

from sqlalchemy import (
    REAL,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


MEMORY_STATUS_VALUES = ("active", "deprecated", "superseded")

memory_tags = Table(
    "memory_tags",
    Base.metadata,
    Column("memory_id", UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="api")
    source_agent: Mapped[str | None] = mapped_column(String(255))
    memory_type: Mapped[str | None] = mapped_column(String(50))
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    classified_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    flags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    project: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")
    status: Mapped[str] = mapped_column(
        Enum(*MEMORY_STATUS_VALUES, name="memory_status", create_type=False),
        nullable=False,
        server_default="active",
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="SET NULL"),
        nullable=True,
    )
    technologies: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    confidence: Mapped[float] = mapped_column(REAL, nullable=False, server_default="0.75")

    __table_args__ = (
        CheckConstraint(
            "status != 'superseded' OR superseded_by IS NOT NULL",
            name="chk_superseded_has_pointer",
        ),
    )

    tags: Mapped[list["Tag"]] = relationship(secondary=memory_tags, back_populates="memories", lazy="selectin")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))

    memories: Mapped[list["Memory"]] = relationship(secondary=memory_tags, back_populates="tags", lazy="noload")

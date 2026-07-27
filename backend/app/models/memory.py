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

from app.utils.ids import new_id

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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="api")
    source_agent: Mapped[str | None] = mapped_column(String(255))
    # The corroboration-independence key, stamped at capture (doc 05 §2.1).
    # Every downstream verification count is COUNT(DISTINCT origin_key).
    origin_key: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class MemoryBuffer(Base):
    """The durable Tier-B landing zone for accepted-but-unprocessed captures.

    Doc 04 §8.6. Capture commits a row here and acks; the flush worker claims it
    with ``FOR UPDATE SKIP LOCKED`` and runs the five-phase pipeline. Durability
    is the whole point — an in-process queue loses the backlog on restart, and
    this tier exists so an accepted capture cannot be lost.

    ``id`` is minted by the caller at accept (UUIDv7) rather than defaulted here,
    because a 202 has to hand back a real handle before the pipeline has run, and
    that same id becomes the ``memories`` row's id at flush.

    Caller-supplied fields with no column of their own — ``memory_type``,
    ``tags``, ``importance``, ``expires_at``, ``source_agent``, ``origin_key`` —
    ride ``metadata_`` and are replayed verbatim at flush. Doc 04 §8.6 is
    explicit that the buffer may never silently drop a captured field.
    """

    __tablename__ = "memory_buffer"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    project: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # none_as_null: without it SQLAlchemy encodes a Python None as JSON `null`
    # rather than SQL NULL, so `WHERE metadata IS NULL` triage silently
    # matches nothing.
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB(none_as_null=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'claimed', 'done', 'error')",
            name="memory_buffer_status_check",
        ),
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))

    memories: Mapped[list["Memory"]] = relationship(secondary=memory_tags, back_populates="tags", lazy="noload")


TAG_NAME_MAX_LENGTH: int = Tag.__table__.c.name.type.length
TAG_CATEGORY_MAX_LENGTH: int = Tag.__table__.c.category.type.length


def tag_category(name: str) -> str | None:
    """The `tags.category` a tag name implies, by the `category/value` convention.

    One definition, beside the columns it has to fit: the capture door validates
    a submitted tag against these lengths and the tag writers derive the column
    from the same rule, so a second copy of either would let a tag pass
    validation and then truncate on write.
    """
    return name.split("/")[0] if "/" in name else None

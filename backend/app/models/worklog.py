from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Computed, DateTime, ForeignKey, Identity, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Workstream(Base):
    """One piece of a client's work in a project: a plan, a design, a task.

    Operational state, not knowledge: nothing here is extracted, ranked with
    memories, or verified (spec 2026-09-23 §7).
    """

    __tablename__ = "workstreams"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    project: Mapped[str] = mapped_column(Text, nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    client: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retain: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_entry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WorklogEntry(Base):
    """One append-only entry: a checkpoint, a ledger chunk or a note."""

    __tablename__ = "worklog_entries"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    workstream_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workstreams.id", ondelete="CASCADE"), nullable=False
    )
    run_key: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', body)", persisted=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

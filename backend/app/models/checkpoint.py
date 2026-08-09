from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SessionCheckpoint(Base):
    """One agent run's note to its successor (spec §Feature-2, T3.16).

    **Operational, not vault knowledge.** There is no verification column here
    and there must not be one: a checkpoint is what an agent said about its own
    run, not a claim any ladder judged, and a rung on it would be an unearned
    badge on unverified prose. T3.18 owns that rule; this model is where the
    absence lives.

    Keyed on ``origin_key`` — the agent-run identity capture already stamps
    (T1.11) — so a checkpoint and the memories from the same run share a key
    without this table referencing ``memories``. They are correlated, never
    joined.
    """

    __tablename__ = "session_checkpoints"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    origin_key: Mapped[str] = mapped_column(Text, nullable=False)
    project: Mapped[str] = mapped_column(Text, nullable=False, default="default")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    next_steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

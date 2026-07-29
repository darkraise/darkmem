from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class Project(Base):
    """The minimal namespace registry (doc 04 §7, baseline `0001_baseline.py`).

    `name` is a case-sensitive primary key and deliberately uncanonicalised —
    `compute_triple_key` embeds `project` verbatim, so `Foo` and `foo` are
    distinct scopes and must stay distinct rows here too (E2 amendment log,
    2026-07-29, T2.01/T2.07/T2.10). Rows are written by lazy registration
    (`app.services.project_registry`), never by this model's own `session.add`
    in application code — that would round-trip on every capture.
    """

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    properties: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

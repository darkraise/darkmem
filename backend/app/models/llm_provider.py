"""ORM model for the LLM provider table.

One row per vendor connection. A purpose row references it by name and
contributes only what varies per purpose (model, params, dimensions,
reasoning, classifier_kind), so a credential rotation reaches every purpose
that uses the provider with no re-apply step.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LLMProviderRow(Base):
    __tablename__ = "llm_providers"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    api_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    api_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )

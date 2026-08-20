"""ORM model for the LLM configuration table.

darkmem is not an LLM proxy. The provider/profile/ml-profile indirection
of the old schema is gone — ``llm_profiles`` and ``ml_profiles`` are
dropped and never exist in the baseline (doc 04 §7, doc 19 §3) — but
``llm_providers`` was reinstated by the owner ruling of 2026-08-20,
reversing that flattening. A purpose row references its provider by name
rather than carrying connection details inline; resolution is one query
with one join.

The ``classification`` purpose additionally carries ``classifier_kind``
(``llm`` | ``local``), which re-homes the in-process classifier inline
rather than referencing the deleted ``ml_profiles``. When the ``[ml]``
extra is absent, classification falls back to the LLM-backed classifier.

The six rows themselves are written by the setup wizard's finalize step
from ``app.services.llm_seed``, never by a migration.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LLMPurposeConfigRow(Base):
    """One row per pipeline purpose (embedding/extraction/...).

    Connection details (vendor, base URL, key) live on the referenced
    ``llm_providers`` row, never inline here.
    """

    __tablename__ = "llm_purpose_configs"

    purpose: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_name: Mapped[str] = mapped_column(
        String(64), ForeignKey("llm_providers.name", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    classifier_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )

    # No __table_args__: the ORM previously declared a redundant
    # UNIQUE(purpose) over the primary key that was never created in the
    # database (schema inventory §9.1), so there is nothing to carry.

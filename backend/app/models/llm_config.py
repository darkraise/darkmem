"""ORM model for the LLM configuration table.

``llm_profiles`` and ``ml_profiles`` are dropped and never exist in the
baseline (doc 04 §7, doc 19 §3), and neither does any ``*_id`` column
pointing at them. ``llm_providers`` is the one level of that indirection
the owner reinstated, on 2026-08-20, because a credential rotation has to
reach every purpose that uses it with no re-apply step: a purpose row
names its provider rather than carrying the connection inline.

Storage is the only thing that changed. ``get_llm_config`` resolves in one
query with one join and still returns a flat ``LLMPurposeConfig``, which is
what keeps the benchlib cache key and the judge identity hash stable —
"darkmem is not an LLM proxy" still holds at runtime.

The ``classification`` purpose additionally carries ``classifier_kind``
(``llm`` | ``local``), which re-homes the in-process classifier inline
rather than referencing the deleted ``ml_profiles``. When the ``[ml]``
extra is absent, classification falls back to the LLM-backed classifier.

The eight purpose rows and the provider rows they name are written by the
setup wizard's finalize step from ``app.services.llm_seed``, never by a
migration.
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

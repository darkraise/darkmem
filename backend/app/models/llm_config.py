"""ORM model for the LLM configuration table.

darkmem is not an LLM proxy, so the provider/profile/ml-profile
indirection is gone: ``llm_providers``, ``llm_profiles`` and
``ml_profiles`` are dropped and never exist in the baseline (doc 04 §7,
doc 19 §3). What remains is **one table of inline rows** — one per
pipeline purpose — each carrying its own connection details.

The ``classification`` purpose additionally carries ``classifier_kind``
(``llm`` | ``local``), which re-homes the in-process classifier inline
rather than referencing the deleted ``ml_profiles``. When the ``[ml]``
extra is absent, classification falls back to the LLM-backed classifier.

The six rows themselves are written by the setup wizard's finalize step
from ``app.services.llm_seed``, never by a migration.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LLMPurposeConfigRow(Base):
    """One row per pipeline purpose (embedding/extraction/...).

    Every connection field is inline, so resolution is one row read and no
    joins. ``api_kind`` is the sole home for vendor wire-protocol quirks.
    """

    __tablename__ = "llm_purpose_configs"

    purpose: Mapped[str] = mapped_column(String(64), primary_key=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    # Kept pending T1.01's call (schema inventory F-10): doc 04 §7's inline
    # field list omits it, but it exists at HEAD and the read path uses it.
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="ollama")
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    api_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    classifier_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )

    # No __table_args__: the ORM previously declared a redundant
    # UNIQUE(purpose) over the primary key that was never created in the
    # database (schema inventory §9.1), so there is nothing to carry.

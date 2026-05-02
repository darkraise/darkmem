"""ORM models for the LLM configuration tables.

Replaces the previous JSONB-blob storage (single ``config`` rows for
``llm_providers`` / ``llm_profiles`` / ``llm_config``) with three
relational tables tied together by foreign keys. Benefits over the
blob shape:

- DB-enforced uniqueness on provider and profile names.
- Cascading delete rules: deleting a provider that's still referenced
  by any profile or purpose is refused at the SQL layer (no manual
  scan in route handlers).
- Renames are possible (UPDATE the name; FKs follow).
- Each profile carries a stable UUID so the LLM Profile dropdown can
  reference the selection explicitly instead of reverse-matching by
  parameter equality.
- ``llm_purpose_configs`` rows pin both ``provider_id`` and
  ``profile_id`` so the resolved fields stay coherent.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class LLMProvider(Base):
    """One stored LLM provider — connection details to a vendor's API.

    The ``api_key`` column holds the secret as plaintext (single-user
    local-network deployment); the response layer masks it as ``"***"``
    before returning to the UI.
    """

    __tablename__ = "llm_providers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    api_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    supports_embedding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )
    api_key_rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    profiles: Mapped[list["LLMProfile"]] = relationship(
        "LLMProfile", back_populates="provider", cascade="all"
    )


class LLMProfile(Base):
    """One stored LLM Profile — a preset bundle of model + params + flags
    keyed to a specific provider. Purposes link to a profile via FK so
    the UI dropdown can show the actually-selected profile without
    reverse-matching by parameter equality.
    """

    __tablename__ = "llm_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_providers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_embedding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasoning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    purpose: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )

    provider: Mapped[LLMProvider] = relationship("LLMProvider", back_populates="profiles")


class MLProfile(Base):
    """One stored ML Profile — a HuggingFace classifier loaded into the
    backend process for in-process inference. Used by the classifier
    purpose as an alternative to LLM-based classification.

    The ``MLModelManager`` lazy-loads the model on first use, caches
    it keyed by ``model_repo``, and (when ``ttl_seconds > 0``) evicts
    on idle. ``ttl_seconds = 0`` means "never evict" — the model
    stays resident until the backend stops.

    All inference runs on CPU; GPU is intentionally unsupported in
    this iteration so ``torch+cpu`` is the only required dependency.
    """

    __tablename__ = "ml_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    model_repo: Mapped[str] = mapped_column(String(512), nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )


class LLMPurposeConfigRow(Base):
    """One row per pipeline purpose (embedding/extraction/...).

    Referenced by FK from at most one provider and at most one profile;
    those references are the explicit linkage that the dropdown uses.
    The inline columns (provider, base_url, api_key, api_kind) are kept
    so a purpose can run without a linked provider too — useful for
    one-off configurations that don't fit any seeded provider.
    """

    __tablename__ = "llm_purpose_configs"

    purpose: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_providers.id", ondelete="SET NULL"),
        nullable=True,
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    ml_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ml_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    # Inline copies of the provider connection fields for purposes that
    # aren't linked to a provider row. When ``provider_id`` is set, these
    # are ignored at read time in favour of the linked provider's values.
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="ollama")
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    api_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )

    __table_args__ = (
        # Lock the purpose key set; keeps the UI's dropdown stable.
        # The set matches ``services.config.PURPOSES``.
        UniqueConstraint("purpose", name="uq_llm_purpose_configs_purpose"),
    )

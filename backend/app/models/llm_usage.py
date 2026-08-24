"""One row per LLM vendor call: what it cost and what caused it.

Deliberately **not** the ``events`` table, for the reason ``JobRun``'s own
docstring already gives: that substrate is append-only by trigger, permanent by
ruling, and doc 17 §5.1's verification metrics are SQL over it alone. Token
metering is the same shape as job telemetry — high volume, individually
near-worthless, and it wants pruning — so it goes where DELETE is ordinary and
``llm_usage_cleanup`` can hold it to a ceiling.

``subject_id`` is Text rather than UUID because two of the six subject kinds are
not uuids. A job run is ``{job_key}@{started_at}``: the ``job_runs`` row is
written only after the runner returns, and a run reporting nothing writes no row
at all, so its id does not exist when the call is made. Search and chat subjects
are request ids.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LLMUsage(Base):
    """One vendor call, priced at the moment it was paid for."""

    __tablename__ = "llm_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    api_kind: Mapped[str] = mapped_column(String(32), nullable=False)

    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    project: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: NULL, never 0, when the vendor reported no envelope. A number nobody
    #: observed is not zero (``benchlib/twin.py``'s doctrine).
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Hidden chain-of-thought, billed inside ``completion_tokens`` by reasoning
    #: models. Broken out because it is a prime candidate for wasted spend and
    #: is unrecoverable later if flattened away at write time.
    reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_measured: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    #: Micro-USD. NULL means "no rate for this model", which is not zero — a
    #: local model priced at a measured 0 is a different state entirely.
    cost_micros: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    #: The three rates actually applied, so the arithmetic can be audited
    #: without knowing what the price table said that day.
    rates_used: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    #: The whole envelope. Flattening to four integers would make a question
    #: nobody has thought of yet unanswerable against history already paid for.
    usage_raw: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    ok: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    error_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        Index("ix_llm_usage_subject", "subject_type", "subject_id"),
        Index("ix_llm_usage_occurred", "occurred_at"),
        Index("ix_llm_usage_purpose_occurred", "purpose", "occurred_at"),
    )

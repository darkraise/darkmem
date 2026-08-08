import uuid
from datetime import datetime

from sqlalchemy import (
    REAL,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.utils.ids import new_id

from .base import Base


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    memory_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    # Inert until T2.27 (the code deriver). A repo id here is the code-side
    # analog of a memory id: it lets code assert a graph row without a memory.
    repo_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("name", "entity_type"),)


class EntityRelation(Base):
    __tablename__ = "entity_relations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False,
    )
    rel_type: Mapped[str] = mapped_column(String(100), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    weight: Mapped[float] = mapped_column(Float, default=0.5)
    memory_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    # Inert until T2.27 — see Entity.repo_ids.
    repo_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source_entity_id", "target_entity_id", "rel_type"),
    )


class KnowledgeTriple(Base):
    __tablename__ = "knowledge_triples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)
    # Soft references, deliberately without ForeignKey (doc 04 §8.3): the
    # graph side deletes entities aggressively, but this table's contract is
    # invalidate-not-delete, so an expired triple must survive its endpoints.
    # subject_name / object_name carry the durable identity instead.
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    subject_name: Mapped[str] = mapped_column(Text, nullable=False)
    object_name: Mapped[str] = mapped_column(Text, nullable=False)
    rel_type: Mapped[str] = mapped_column(Text, nullable=False)
    valid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reference_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    project: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")
    triple_key: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="candidate")
    confidence: Mapped[float | None] = mapped_column(REAL)
    applies_when: Mapped[dict | None] = mapped_column(JSONB)
    learned_in: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    review_state: Mapped[str | None] = mapped_column(Text)
    source_file: Mapped[str | None] = mapped_column(Text)
    # Doc 08 §4.3's demotion hysteresis. The marker is the `under-sourced`
    # label — an overlay on a still-`corroborated` row, never a fifth
    # verification_status — and the counter is the grace bookkeeping, since
    # the window is fixed in consecutive recompute cycles rather than in time.
    demotion_pending_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    demotion_pending_cycles: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # Doc 08 §6's third review opener (T2.112), shaped after the pair above
    # rather than invented: the marker is what the reviewer's queue derives
    # `contradiction-suspected` from, and it is emphatically **not** a rung —
    # a flagged fact keeps its `verification_status`, its badge and its place
    # in retrieval while a human looks.
    #
    # **Why a column and not a read of the scan's journal.** The finding is
    # re-derived, guards and all, by `detect_scanned_contradiction` on every
    # recompute; the ladder writes the result here in the *same* UPDATE as
    # `verification_status`, exactly as `demotion_pending_since` rides it. So
    # this is a cache the authority refreshes each cycle, not a frozen verdict
    # — the same staleness contract the sibling marker already has. The
    # alternative (the queue reading the journal itself) would put an
    # `app.services.contradiction_veto` import on a read surface, which
    # invariant 15's source scan fails the build on, and rightly: adjudication
    # stays reachable from the ladder alone.
    #
    # The counterpart id rides beside the timestamp because doc 08 §6 wants
    # both sides labelled, and a reviewer asked to confirm a contradiction
    # against a counterpart they cannot see is not reviewing. It carries no FK
    # on purpose: facts are invalidate-not-delete, so the counterpart outlives
    # its own retirement, and a cascade here would blank the evidence for the
    # flag at exactly the moment it mattered.
    contradiction_suspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contradiction_counterpart_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # T2.85: the expiry the fact's own text states, recorded at lift time and
    # spent by the recompute arm, which writes `invalid_at := stated_expiry`
    # once the date passes. Not written to `invalid_at` at lift time (that
    # column is only-ever-past by contract, and a future value drops the fact
    # out of the open-belief predicate the day it is written), and not to
    # `expired_at` (which `as_of` ignores, so the historical question would
    # answer wrongly for every instant past the stated date).
    stated_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

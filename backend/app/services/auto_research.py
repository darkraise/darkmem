"""The F7 research loop: gather evidence outside the box, file it through the
ordinary capture front door (doc 09 §6, T3.07).

**This is orchestration, not a pipeline.** Every finding is filed through
``MemoryService.batch_create_memories`` — the same service call the four
capture doors funnel into — so extraction, classification, the buffer, and the
ladder treat a researched memory exactly as they treat any other. The loop
reaches nothing under ``app.services`` that capture does not already reach for
it; ``tests/test_auto_research.py`` pins the module's whole ``app.*`` import set
to a whitelist so a second ingestion path cannot appear here by accident.

**Evidence gathering lives outside the box** (invariant 1, doc 09 §6): web
search and fetch are the calling agent's capability, never a darkmem datastore.
So ``ResearchGatherer`` is a port with no in-tree implementation, and that
absence is a design position rather than an omission — a gatherer backed by a
model alone would *invent* sources, and inventing sources is the one failure
this loop's origin discipline exists to prevent. Whoever owns a real
web-capable agent injects it.

**The loop manufactures origins; it does not observe them, and the corpus must
be able to tell the difference** (v0.5 spec, Half B). Two markers make that
machine-checkable rather than remembered: every researched capture carries
``source = RESEARCH_SOURCE`` and an ``origin_key`` that ``is_researched_origin``
recognises, so a later measurement can slice manufactured origins out of a
count instead of pooling them silently. Forging the marker from outside can
only *widen* the manufactured slice, which is the safe direction for a
disclosure — a researched capture can never lose its marker, because this
module is the only thing that files one.

**Today every researched capture is ONE origin, deliberately.** Establishing
per-source identity is T3.08's task; until it lands, ``research_origin_id``
returns ``None`` for every finding and ``resolve_origin_key`` folds the run
into the capture layer's merge-to-one bucket. That undercounts — the direction
doc 09 §6 requires — so this loop on its own cannot promote anything off
``candidate``. Minting a per-run key instead would be the counterfeit: two runs
over the same page are the same source fetched twice, which is exactly the
shape "merge to one origin, never mint distinct ones" names.

**A failed run leaves nothing behind.** Gathering completes before anything is
written, the whole run is filed in a single ``batch_create_memories`` call
(hence a single transaction and a single commit), and any failure rolls that
transaction back before re-raising. A budget the run cannot satisfy refuses the
whole run rather than filing a truncated one: filing part of a research run
would leave a corpus whose origin story is untrue in a way nothing downstream
could detect.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mcp.client_identity import resolve_origin_key
from app.models.config import Config
from app.schemas.memory import MemoryBatchCreate, MemoryCreate
from app.services.events import record_event
from app.services.memory import MemoryService
from app.utils.ids import new_id

logger = logging.getLogger(__name__)

# The reserved source-kind. Every capture this loop files carries it, so
# `memories.source` alone distinguishes a manufactured origin from an observed
# one without joining anything.
RESEARCH_SOURCE = "research"

AUTO_RESEARCH_CONFIG_KEY = "auto_research"

# Fail closed. Building the loop is not running it (T3.07 brief): pointing it
# at a live instance is a separate, owner-owned decision, so an install that
# has never been configured refuses every run.
AUTO_RESEARCH_DEFAULTS: dict[str, object] = {
    "enabled": False,
    "max_findings_per_run": 20,
    "max_content_chars": 8000,
}

# The batch door's own cap, read off the schema rather than re-typed, so the
# budget cannot quietly authorise a batch the front door would reject.
MAX_FINDINGS_CEILING: int = next(
    meta.max_length
    for meta in MemoryBatchCreate.model_fields["entries"].metadata
    if getattr(meta, "max_length", None) is not None
)


class ResearchBudgetExceeded(Exception):
    """The gathered evidence does not fit the configured budget.

    Raised before anything is written. Refusing the run is deliberate: a
    truncated filing would record a research run that claims to have gathered
    what it did not file.
    """


class ResearchDisabled(Exception):
    """The `auto_research` config row does not permit runs on this install."""


@dataclass(frozen=True)
class ResearchFinding:
    """One piece of evidence the gatherer brought back.

    ``source_id`` is the gatherer's own identity for the source it came from —
    a canonical URL, a document id. It is carried through to the memory's
    metadata and is what T3.08 will resolve into a distinct origin; today it
    only documents provenance and changes no count.
    """

    content: str
    source_id: str | None = None
    metadata: dict = field(default_factory=dict)


class ResearchGatherer(Protocol):
    """The evidence-gathering capability, which lives outside darkmem's box.

    Implementations do the searching and fetching and return at most ``limit``
    findings. Returning more is a contract violation the loop refuses rather
    than trims.
    """

    async def gather(self, subject: str, *, limit: int) -> Sequence[ResearchFinding]:
        ...


@dataclass(frozen=True)
class ResearchBudget:
    enabled: bool
    max_findings_per_run: int
    max_content_chars: int


@dataclass(frozen=True)
class ResearchRunResult:
    run_id: UUID
    subject: str
    project: str
    gathered: int
    filed: int
    memory_ids: tuple[UUID, ...]
    journalled: bool


def _positive_int(value: object, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return default
    return value


async def load_budget(session: AsyncSession) -> ResearchBudget:
    """The per-run budget, from the `auto_research` config row over defaults.

    A malformed row degrades to the defaults rather than raising: the budget
    bounds a run, and an unreadable bound must never read as "unbounded".
    """
    row = (await session.execute(
        select(Config).where(Config.key == AUTO_RESEARCH_CONFIG_KEY)
    )).scalar_one_or_none()
    stored = row.value if row is not None and isinstance(row.value, dict) else {}

    max_findings = _positive_int(
        stored.get("max_findings_per_run"),
        int(AUTO_RESEARCH_DEFAULTS["max_findings_per_run"]),
    )
    if max_findings > MAX_FINDINGS_CEILING:
        logger.warning(
            "%s.max_findings_per_run=%d exceeds the capture batch cap %d; clamping",
            AUTO_RESEARCH_CONFIG_KEY, max_findings, MAX_FINDINGS_CEILING,
        )
        max_findings = MAX_FINDINGS_CEILING

    return ResearchBudget(
        enabled=bool(stored.get("enabled", AUTO_RESEARCH_DEFAULTS["enabled"])),
        max_findings_per_run=max_findings,
        max_content_chars=_positive_int(
            stored.get("max_content_chars"),
            int(AUTO_RESEARCH_DEFAULTS["max_content_chars"]),
        ),
    )


def research_origin_id(finding: ResearchFinding) -> str | None:
    """The declared origin identity for one finding, or ``None`` to merge.

    **T3.08's seam.** Returning ``None`` for every finding is what makes a
    whole research run one origin today: ``resolve_origin_key`` falls back to
    the capture layer's merge-to-one bucket, which counts once and can never
    fire a corroboration gate on its own. T3.08 replaces this body with real
    per-source identity — the same URL fetched twice must still resolve to one
    id — and every other line of this module stays as it is, because the call
    site below is already per-finding.
    """
    return None


def research_origin_key(finding: ResearchFinding, *, project: str) -> str:
    """The `origin_key` a researched capture is stamped with.

    Routed through T1.11's ``resolve_origin_key`` rather than formatted here,
    so researched captures inherit the same declared-identity-then-merge chain
    every other door uses, with ``RESEARCH_SOURCE`` as the source.
    """
    return resolve_origin_key(
        research_origin_id(finding), None, source=RESEARCH_SOURCE, project=project,
    )


def is_researched_origin(origin_key: str | None) -> bool:
    """Whether an `origin_key` was manufactured by this loop.

    The disclosure the v0.5 spec asks to be machine-enforced: a measurement
    that pools manufactured origins with observed ones has to do so on
    purpose. Both shapes are recognised — the merged bucket this task files
    under (``unknown:research:<project>``) and the declared form T3.08 will
    mint (``research:<id>``) — so the predicate does not have to change when
    the seam is filled.
    """
    if not origin_key:
        return False
    key = origin_key.strip().lower()
    return key.startswith(f"{RESEARCH_SOURCE}:") or key.startswith(
        f"unknown:{RESEARCH_SOURCE}:"
    )


def _build_entries(
    findings: Sequence[ResearchFinding],
    *,
    subject: str,
    project: str,
    run_id: UUID,
    budget: ResearchBudget,
) -> list[MemoryCreate]:
    if len(findings) > budget.max_findings_per_run:
        raise ResearchBudgetExceeded(
            f"gatherer returned {len(findings)} findings for subject {subject!r}, "
            f"over the {budget.max_findings_per_run} the budget allows"
        )
    for index, finding in enumerate(findings):
        if len(finding.content) > budget.max_content_chars:
            raise ResearchBudgetExceeded(
                f"finding {index} for subject {subject!r} is "
                f"{len(finding.content)} characters, over the "
                f"{budget.max_content_chars} the budget allows"
            )

    entries = [
        MemoryCreate(
            content=finding.content,
            project=project,
            source=RESEARCH_SOURCE,
            origin_key=research_origin_key(finding, project=project),
            metadata={
                **finding.metadata,
                "research": {
                    "run_id": str(run_id),
                    "subject": subject,
                    "source_id": finding.source_id,
                },
            },
        )
        for finding in findings
    ]
    # Validated through the batch door's own schema, so the run inherits its
    # 1-100 cap and its per-entry validation instead of carrying a second copy
    # of either.
    return list(MemoryBatchCreate(entries=entries).entries)


async def run_research(
    session: AsyncSession,
    *,
    subject: str,
    project: str,
    gatherer: ResearchGatherer,
    service: MemoryService | None = None,
    budget: ResearchBudget | None = None,
) -> ResearchRunResult:
    """Gather evidence for ``subject`` and file it into ``project``.

    Owns ``session``'s transaction for the duration: capture commits, and a
    failure rolls back, so a caller must not hand this a session carrying work
    of its own — and a ``service`` passed in must be bound to that same
    session, or the rollback below reaches a transaction the write did not use.

    The two stages are strictly ordered and never interleaved. Gathering
    finishes first, so a gatherer that fails partway through has written
    nothing; filing is then one call, so there is no window in which some
    findings are durable and others are not.
    """
    budget = budget or await load_budget(session)
    if not budget.enabled:
        raise ResearchDisabled(
            f"the {AUTO_RESEARCH_CONFIG_KEY} config row does not enable research runs"
        )

    run_id = new_id()
    findings = list(await gatherer.gather(subject, limit=budget.max_findings_per_run))
    if not findings:
        logger.info("research run %s for %r gathered nothing", run_id, subject)
        return ResearchRunResult(
            run_id=run_id, subject=subject, project=project,
            gathered=0, filed=0, memory_ids=(), journalled=False,
        )

    entries = _build_entries(
        findings, subject=subject, project=project, run_id=run_id, budget=budget,
    )
    service = service or MemoryService(session)
    try:
        results = await service.batch_create_memories(entries, api_key_id=None)
    except Exception:
        await session.rollback()
        raise

    memory_ids = tuple(result.ack.id for result in results)
    # Counts and identity only. The findings' text is already durable on the
    # memory rows, and the journal outlives their deletion (T2.59), so copying
    # content here would widen the residue for nothing this run needs.
    journalled = await record_event(
        session,
        event_type="research_run",
        object_type="system",
        project=project,
        source=RESEARCH_SOURCE,
        payload={
            "run_id": str(run_id),
            "subject": subject,
            "filed": len(memory_ids),
            "memory_ids": [str(memory_id) for memory_id in memory_ids],
            "origins_manufactured": True,
        },
    )
    if not journalled:
        # Not fatal, and deliberately so: the disclosure a later measurement
        # reads is the marker on the memory rows themselves, which is already
        # committed. The journal is the run-level audit on top of it.
        logger.warning("research run %s filed %d memories unjournalled", run_id, len(memory_ids))
    await session.commit()

    return ResearchRunResult(
        run_id=run_id, subject=subject, project=project,
        gathered=len(findings), filed=len(memory_ids),
        memory_ids=memory_ids, journalled=journalled,
    )

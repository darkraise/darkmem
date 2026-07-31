"""The deterministic same-endpoint contradiction scan — the veto's input today.

Doc 08 §4.2 names two inputs to the fact-level veto: this deterministic
same-endpoint scan and the Tier-C LLM contradiction scan (§5.3, T2.11). Only the
deterministic half lives here. A memory-level ``CONTRADICTS`` edge may *flag* a
fact for scanning but is never itself the verdict, because truth is adjudicated
at the fact layer where the provenance lives.

**Precision first, and the direction of error is fixed.** A missed contradiction
delays a dispute, which doc 08 §5.3 names the preferred failure; a manufactured
one demotes a correctly-corroborated fact and buries a real dispute under noise.
So this scan fires only on pairs whose incompatibility is decidable from the
closed relation vocabulary alone, with no model and no judgment:

1. ``single_valued`` — two live facts in one project sharing ``subject_name``
   and ``rel_type`` but naming different objects, where the relation admits at
   most one object per subject. ``SINGLE_VALUED_RELATIONS`` is deliberately tiny
   (below): a project legitimately ``USES`` many tools and a service is
   legitimately ``DEPLOYED_ON`` many hosts, and telling "also true" from
   "instead of" on those needs the model T2.11 wires.
2. ``inverse_replacement`` — a REPLACES-family edge asserted in both directions
   between the same two names. Directed succession cannot run both ways over one
   window. ``REPLACES_FAMILY`` is imported rather than re-typed, because the
   family is one bucket everywhere else in this codebase and narrowing it here
   would be a silent behaviour change.

Both survivors then have to clear two independent guards, and each guard is the
whole reason a real system's version of this scan does not degenerate into
noise: the windows must overlap (disjoint windows are succession the belief axis
already models, §3.1), and the counterpart must carry an attributable origin the
subject fact does not — one source restating itself is an echo, not testimony.

**Nothing here reads configuration.** The veto is absolute (doc 08 §4.2): not a
weight, not a score, not tunable. There is no threshold to tighten and no flag to
clear, and ``tests/test_contradiction_veto.py`` fails the build if this module
grows a config read.

**Tier-C only (invariant 15).** This is an input to the verification ladder, so
the same rule binds it: nothing in capture or retrieval may reach it.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fact_sources import FactSourceRepository
from app.services.relations import REPLACES_FAMILY

logger = logging.getLogger(__name__)

# Relations where one subject admits at most one object at a time, so a second
# object over the same window is a genuine conflict rather than a second true
# statement. Every other member of RELATIONSHIP_TYPES is multi-valued in normal
# use, and a deterministic scan has no way to tell an additional truth from a
# replacement without reading the sentences — which is T2.11's job, not this
# one's. Widening this set is a semantic claim about the relation, not a tuning
# knob: it belongs in a task with a stated warrant.
SINGLE_VALUED_RELATIONS: frozenset[str] = frozenset({"HAPPENED_ON"})

RULE_SINGLE_VALUED = "single_valued"
RULE_INVERSE_REPLACEMENT = "inverse_replacement"

_FACT_COLUMNS = (
    "id, project, subject_name, rel_type, object_name, "
    "valid_at, invalid_at, expired_at"
)

_SINGLE_VALUED_SQL = """
    SELECT id, valid_at, invalid_at
    FROM knowledge_triples
    WHERE project = CAST(:project AS text)
      AND expired_at IS NULL
      AND subject_name = CAST(:subject_name AS text)
      AND rel_type = CAST(:rel_type AS text)
      AND object_name <> CAST(:object_name AS text)
      AND id <> CAST(:fact_id AS uuid)
    ORDER BY created_at, id
"""

_INVERSE_REPLACEMENT_SQL = """
    SELECT id, valid_at, invalid_at
    FROM knowledge_triples
    WHERE project = CAST(:project AS text)
      AND expired_at IS NULL
      AND subject_name = CAST(:object_name AS text)
      AND object_name = CAST(:subject_name AS text)
      AND rel_type = ANY(CAST(:family AS text[]))
      AND id <> CAST(:fact_id AS uuid)
    ORDER BY created_at, id
"""


@dataclass(frozen=True)
class ContradictionFinding:
    """One adjudicated contradiction, and everything that produced it.

    Returned whole rather than as a bare boolean so the verdict can explain
    itself: T2.06 journals the transition and G-C counts it, and a dispute
    nobody can trace back to a counterpart fact and a named witness origin is a
    dispute nobody can review.
    """

    fact_id: str
    counterpart_id: str
    rule: str
    witness_origin: str


def windows_overlap(
    a_valid: datetime | None,
    a_invalid: datetime | None,
    b_valid: datetime | None,
    b_invalid: datetime | None,
) -> bool:
    """Do two belief windows overlap? Half-open ``[valid_at, invalid_at)``.

    NULL ``valid_at`` reads as unbounded-past and NULL ``invalid_at`` as
    open-ended (doc 08 §3.1, and the same reading ``as_of`` implements), so a
    row with neither bound overlaps everything. That is what makes the succession
    case work rather than what breaks it: the stale-on-arrival pass (§3.2) closes
    the older row's window *before* the newer open-ended row inserts, so
    postgres-in-2024 versus mysql-in-2025 arrive as two bounded, disjoint windows
    and never reach the veto. Two rows that are *both* still open-ended are two
    live simultaneous beliefs, and those genuinely do conflict.

    The boundary is exclusive at the closing end so that adjacent windows the
    disjoint-window pass produces — one closing exactly where the next opens —
    are not read as an overlap.
    """
    if a_invalid is not None and b_valid is not None and b_valid >= a_invalid:
        return False
    if b_invalid is not None and a_valid is not None and a_valid >= b_invalid:
        return False
    return True


async def _attributable_origins(
    session: AsyncSession, fact_id: UUID | str
) -> tuple[str, ...]:
    """The normalised origins that identify a witness for this fact.

    Reuses ``FactSourceRepository.origin_profile`` rather than re-deriving the
    NULL-origin folding rule: unknown identity is one merged bucket that carries
    no session identity, so it counts toward K but can never *be* the distinct
    witness a non-echo contradiction requires — the same doctrine that keeps it
    out of the promotion gates.
    """
    profile = await FactSourceRepository(session).origin_profile(fact_id)
    return tuple(
        origin.origin_key
        for origin in profile.attributable_origins
        if origin.origin_key is not None
    )


async def detect_open_contradiction(
    session: AsyncSession, fact_id: UUID | str
) -> ContradictionFinding | None:
    """The deterministic scan. First finding wins; ``None`` means none found.

    ``None`` is "this scan found nothing", never "the fact is true". The
    conjunction of every wired detector is what an adjudicated-clean verdict
    means (see ``adjudicate_contradiction``).

    An expired fact is not adjudicated: belief in it has been withdrawn, it is
    retained history rather than a served claim, and disputing history says
    nothing anyone can act on.
    """
    result = await session.execute(
        text(
            f"SELECT {_FACT_COLUMNS} FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    subject = result.mappings().first()
    if subject is None:
        logger.debug("detect_open_contradiction: no knowledge_triples row for %s", fact_id)
        return None
    if subject["expired_at"] is not None:
        return None

    params = {
        "fact_id": str(subject["id"]),
        "project": subject["project"],
        "subject_name": subject["subject_name"],
        "object_name": subject["object_name"],
        "rel_type": subject["rel_type"],
    }
    arms: list[tuple[str, str, dict]] = []
    if subject["rel_type"] in SINGLE_VALUED_RELATIONS:
        arms.append((RULE_SINGLE_VALUED, _SINGLE_VALUED_SQL, params))
    # A self-loop names one endpoint twice, so its "inverse" is itself and the
    # arm would match every other self-loop on that name.
    if (
        subject["rel_type"] in REPLACES_FAMILY
        and subject["subject_name"] != subject["object_name"]
    ):
        arms.append(
            (
                RULE_INVERSE_REPLACEMENT,
                _INVERSE_REPLACEMENT_SQL,
                {**params, "family": sorted(REPLACES_FAMILY)},
            )
        )
    if not arms:
        return None

    asserting = set(await _attributable_origins(session, subject["id"]))

    for rule, sql, sql_params in arms:
        candidates = await session.execute(text(sql), sql_params)
        for candidate in candidates.mappings().all():
            if not windows_overlap(
                subject["valid_at"],
                subject["invalid_at"],
                candidate["valid_at"],
                candidate["invalid_at"],
            ):
                continue
            for origin in await _attributable_origins(session, candidate["id"]):
                if origin not in asserting:
                    return ContradictionFinding(
                        fact_id=str(subject["id"]),
                        counterpart_id=str(candidate["id"]),
                        rule=rule,
                        witness_origin=origin,
                    )
    return None


ContradictionDetector = Callable[
    [AsyncSession, "UUID | str"], Awaitable[ContradictionFinding | None]
]

# Every detector whose verdict the veto composes. **T2.11's LLM scan joins this
# tuple; it must not be plumbed past it.** Recovery out of `disputed` is
# conjunctive — a fact is only adjudicated clean when every wired detector
# reports nothing — so a scan that reports through a side channel would let this
# one's silence resolve a dispute it cannot see. Registering is what makes a
# detector's finding both able to open a dispute and required to keep it open.
CONTRADICTION_DETECTORS: tuple[ContradictionDetector, ...] = (detect_open_contradiction,)


async def adjudicate_contradiction(session: AsyncSession, fact_id: UUID | str) -> bool:
    """Is there an open contradiction against this fact? A definite verdict.

    ``True`` on the first detector that finds one; ``False`` only when every
    wired detector reported nothing. That conjunction is the whole meaning of
    ``False`` here, and it is why the ladder treats it as permission to leave
    ``disputed`` while treating "no detector ran" as a hold.
    """
    for detector in CONTRADICTION_DETECTORS:
        if await detector(session, fact_id) is not None:
            return True
    return False

"""The deterministic same-endpoint contradiction scan — the veto's one input.

**AMENDED 2026-08-08 (doc 08 §4.2, Tier-3, owner-ratified).** This module used
to hold both of the veto's inputs: the deterministic same-endpoint scan and a
read-back of the Tier-C LLM scan's journalled verdict. Three measured G-D runs
across two vendors put the model arm's contradiction-precision at 0.7937 /
0.8814 / 0.9020 against a 0.95 bar, and no ensemble of the judges measured can
exceed 0.9483 at any recall — so wiring it into an unappealable veto converts
each false positive into a near-permanent manufactured dispute, which is the
one failure §5.3's asymmetry forbids. **The absolute veto now stands on the
deterministic arm alone**, whose precision is by construction.

The model arm's read-back (``detect_scanned_contradiction``) still lives here,
because it re-applies this module's own guards against today's rows and there
is nowhere else those guards are spelled. It is no longer a member of
``CONTRADICTION_DETECTORS``: the ladder reads it as a *review* opener
(§6, contradiction-suspected), leaving the fact its rung and its badge while a
human confirms. A memory-level ``CONTRADICTS`` edge may *flag* a fact for
scanning but is never itself the verdict, because truth is adjudicated at the
fact layer where the provenance lives.

**Precision first, and the direction of error is fixed.** A missed contradiction
delays a dispute, which doc 08 §5.3 names the preferred failure; a manufactured
one demotes a correctly-corroborated fact and buries a real dispute under noise.
So the veto fires only on pairs whose incompatibility is decidable from the
closed relation vocabulary alone, with no model and no judgment:

1. ``single_valued`` — two live facts in one project sharing ``subject_name``
   and ``rel_type`` but naming different objects, where the relation admits at
   most one object per subject. ``SINGLE_VALUED_RELATIONS`` is **empty today**
   — a recorded per-relation pass over the whole vocabulary admitted none, and
   the per-relation reasons are below — so the rule is live and its
   precondition is not met by any relation the taxonomy stores.
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

**The echo test is deliberately asymmetric, and the asymmetry is the point.**
It asks whether the *counterpart* brings a witness the subject fact does not
have, so with subject origins {a} and counterpart origins {a, b} the subject is
disputed while the counterpart, scanned in its own turn, is not: b is new
testimony against the subject's claim, but every origin behind the subject is
already behind the counterpart, so nothing independent disputes it. That is the
correct reading of "the contradicting source is a distinct origin, not the same
one re-stating itself" — the question is always asked of the challenger. A
symmetric rule would dispute both rows on one witness's say-so, which is a vote,
and the veto is not a vote.

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
from app.services.events import CONTRADICTION_DISMISSED, CONTRADICTION_SCANNED
from app.services.relations import REPLACES_FAMILY

logger = logging.getLogger(__name__)

# Relations where one subject admits at most one object at a time, so a second
# object over the same window is a genuine conflict rather than a second true
# statement.
#
# **Empty after a recorded per-relation pass over all sixteen members of
# RELATIONSHIP_TYPES, and that is the finding rather than an omission.**
# Admission requires the taxonomy to *guarantee* at most one object per
# subject — this arm feeds an unappealable veto whose precision is by
# construction, so "usually one" admits nothing. Two mechanisms defeat every
# member.
#
# Rejected as plural by construction — a second object is a second true
# statement, held simultaneously:
#
#   USES         a project uses many tools at once; also absorbs CONFIGURES /
#                APPLIES_TO / COMMUNICATES_WITH, and the rescue layer mints it
#                from "via" / "with" / "to" at 0.55–0.7 confidence
#   DEPENDS_ON   many dependencies at once
#   HAS_PART     a whole has many parts; plurality is the relation's point
#   IMPLEMENTS   one implementer, many protocols and interfaces
#   EXTENDS      specs, languages and frameworks extend several bases; the
#                taxonomy stores no single-inheritance guarantee
#   REPLACES     one successor retires several predecessors at once; the
#                rescue layer also mints it from "instead of" / "builds on"
#                at 0.7–0.75
#   IMPROVES_ON  rust IMPROVES_ON c and IMPROVES_ON c++, both true; BUILDS_ON,
#                plainly plural, also folds in via LEGACY_RELATION_TYPE_MAP
#   IS_A         classification is a lattice, not a function: redis IS_A
#                database and IS_A tool
#   CAUSES       one cause, many effects; PRODUCES and FIXES fold in
#   MENTIONS     a document mentions many things
#   CITES        a paper cites many papers
#   INSPIRED_BY  many inspirations
#
# Rejected because legacy folding stores several senses under one rel_type
# with no discriminator, so a stored row's rel_type never certifies the
# single-valued sense even where one exists:
#
#   DEPLOYED_ON  absorbs RUNS_ON and LOCATED_IN, and the rescue layer routes a
#                bare "on" into it at 0.6 confidence — host, OS, container and
#                platform are all "on" and all true at once
#   AUTHORED_BY  co-authorship is plural on its own, and PUBLISHED_IN (a
#                venue) and WORKS_AT (an employer) fold two more senses in
#   HAPPENED_ON  three senses, detailed below
#   RELATED_TO   the normaliser's own fallback; collects every unrecognised
#                emission plus seven aliases — maximally polyvalent by design
#
# `HAPPENED_ON` is the instructive rejection because it once looked like the
# one admission (an event happens on one date) and had to be withdrawn:
# `normalize_relation_type` folds three different senses into it and stores no
# discriminator between them:
#
#   1. a point occurrence     — "the launch HAPPENED_ON 2024-01-01"
#   2. a span occurrence      — a multi-day conference asserted per day
#   3. a *location*, via LEGACY_RELATION_TYPE_MAP's VISITED -> HAPPENED_ON and
#      LIVES_IN -> HAPPENED_ON, so "alice HAPPENED_ON paris" and "alice
#      HAPPENED_ON tokyo" are both true and both stored under this relation
#
# A relation is single-valued only when *every* sense it stores is, and no
# deterministic predicate over (subject_name, rel_type, object_name) recovers
# sense 1: senses 1 and 2 are both date-shaped, so neither a date parse nor an
# ISO-shape gate separates them.
#
# The exclusive slots the LLM judge measurably misses — a port, a version, a
# TTL, a scrape interval, a bucket name — are *attribute* slots this taxonomy
# does not store as relations at all, so that detection capacity cannot be
# added by widening this set: it needs taxonomy-first single-valued relations
# minted for those slots (doc 06 §3.1), never a veto workaround. Admitting the
# nearest existing relation instead would manufacture disputes out of true
# claims, which is precisely the failure doc 08 §5.3's asymmetry forbids. The
# cost is unchanged: the scan's whole reach today is the inverse-replacement
# rule, and undercounting only delays a dispute.
#
# Widening this is a semantic claim about a relation, never a tuning edit, and
# `tests/test_contradiction_veto.py` fails the build if a member is also a
# target of LEGACY_RELATION_TYPE_MAP — the exact mechanism that made
# `HAPPENED_ON` polyvalent — or is not itself in RELATIONSHIP_TYPES, which
# would arm the rule against a rel_type no stored row can carry.
SINGLE_VALUED_RELATIONS: frozenset[str] = frozenset()

RULE_SINGLE_VALUED = "single_valued"
RULE_INVERSE_REPLACEMENT = "inverse_replacement"

_FACT_COLUMNS = (
    "id, project, subject_name, rel_type, object_name, "
    "valid_at, invalid_at, expired_at"
)

# The candidate projection carries the counterpart's own triple as well as the
# columns the overlap guard reads, because a finding that cannot state the
# competing claim is a finding a human cannot adjudicate (doc 08 §6). The three
# name columns widen the projection only; they are not predicates and change no
# row, no ordering and no verdict.
_CANDIDATE_COLUMNS = (
    "id, valid_at, invalid_at, subject_name, rel_type, object_name"
)

_SINGLE_VALUED_SQL = f"""
    SELECT {_CANDIDATE_COLUMNS}
    FROM knowledge_triples
    WHERE project = CAST(:project AS text)
      AND expired_at IS NULL
      AND subject_name = CAST(:subject_name AS text)
      AND rel_type = CAST(:rel_type AS text)
      AND object_name <> CAST(:object_name AS text)
      AND id <> CAST(:fact_id AS uuid)
    ORDER BY created_at, id
"""

_INVERSE_REPLACEMENT_SQL = f"""
    SELECT {_CANDIDATE_COLUMNS}
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

    The counterpart's triple is carried alongside its id because doc 08 §6's
    "labelled with both sides" is a claim a human reads, and an id alone sends
    every reader back to ``knowledge_triples`` for the sentence. The free-text
    ``fact`` column is deliberately **not** carried: the triple already states
    the competing claim, and this record reaches an append-only journal whose
    payloads outlive deletion of their subject, so every additional copied
    column is a permanent one.

    The three name fields default to ``None`` because a detector is not
    obliged to know them. The deterministic scan reads them off the candidate
    row it already selected; a future registered detector (T2.11's LLM scan)
    that can name only an id says so by leaving them unset rather than by
    inventing a triple.
    """

    fact_id: str
    counterpart_id: str
    rule: str
    witness_origin: str
    counterpart_subject: str | None = None
    counterpart_rel_type: str | None = None
    counterpart_object: str | None = None


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
                        counterpart_subject=candidate["subject_name"],
                        counterpart_rel_type=candidate["rel_type"],
                        counterpart_object=candidate["object_name"],
                    )
    return None


# ── the Tier-C model scan's verdict, read back from the journal ──────────
#
# Not a veto input since 2026-08-08 (doc 08 §4.2's amendment). What reads this
# is the ladder's contradiction-suspected review opener, so a finding here
# flags a fact for a human and moves no rung.

RULE_SCANNED = "llm_scan"

_LATEST_SCAN_SQL = """
    SELECT payload, created_at, id
    FROM events
    WHERE object_type = 'fact'
      AND event_type = CAST(:kind AS text)
      AND object_id = CAST(:id AS uuid)
    ORDER BY created_at DESC, id DESC
    LIMIT 1
"""

# A human dismissal landing after the finding silences it (T2.112), compared on
# the same ``(created_at, id)`` tuple the recency rule above uses so a dismissal
# and a re-scan in one instant order deterministically rather than by which
# query ran first.
#
# **Read-time, like every other guard here, and that placement is the design.**
# Dismissal joins the three clearing grounds in this function's docstring rather
# than short-circuiting them, so a *later* scan legitimately re-flags: the human
# dismissed the finding they were shown, not every finding this pair can produce.
_LATEST_DISMISSAL_SQL = """
    SELECT created_at, id
    FROM events
    WHERE object_type = 'fact'
      AND event_type = CAST(:kind AS text)
      AND object_id = CAST(:id AS uuid)
    ORDER BY created_at DESC, id DESC
    LIMIT 1
"""

_COUNTERPART_SQL = f"""
    SELECT {_CANDIDATE_COLUMNS}
    FROM knowledge_triples
    WHERE id = CAST(:id AS uuid)
      AND expired_at IS NULL
      AND project = CAST(:project AS text)
"""


async def detect_scanned_contradiction(
    session: AsyncSession, fact_id: UUID | str
) -> ContradictionFinding | None:
    """The model scan's standing verdict, re-validated against today's rows.

    The scan runs on its own six-hourly cadence and cannot be consulted
    synchronously — it costs a model call per pair — so its adjudication is
    journalled and read back here. The most recent row wins.

    **A later clean pass really does clear the flag, and that is what the
    rewire bought.** This paragraph used to argue the opposite, and the
    argument was sound while the finding wrote ``disputed``: the scan skips
    facts that are already disputed (doc 08 §5.3), so applying the verdict
    removed the fact from the scan's own working set, no second verdict was
    ever written for it, and a judge false positive stood until a guard lapsed
    or a human ratified. Under doc 08 §4.2's amendment the finding opens review
    instead, so the fact keeps its rung, stays servable, and stays in the
    scan's working set — its next ``sources_changed`` pass writes a fresh
    verdict, and a clean one supersedes this row by the same recency rule. The
    review flag is therefore self-clearing on three independent grounds:

    1. **A later clean verdict**, now genuinely reachable.
    2. **Guard lapse** — the counterpart expires, a window closes, or the
       witness origin joins the subject. Each is re-checked below on every
       read, so a verdict whose grounds have gone stops flagging by itself.
    3. **Human ratification** (doc 08 §4.4). A ratified fact is immune, and
       the ladder is what refuses to carry the flag onto its decision.

    A judge false positive therefore costs a reviewer's glance rather than a
    near-permanent manufactured dispute, which is the whole trade the
    amendment makes: §5.3's sanctioned direction of error is a *delayed*
    dispute, and a flag awaiting confirmation is exactly that.

    **Nothing is trusted from the payload except the pair it names.** A verdict
    can outlive the rows it was made about — the counterpart expires, a window
    closes, the witness origin is withdrawn — and a journal row is append-only,
    so it can never be corrected in place. Every guard the deterministic scan
    applies at selection time is therefore re-applied here at read time against
    the live rows, and the counterpart triple is re-read rather than replayed
    out of the payload. A verdict whose guards no longer hold is silence, not a
    finding.
    """
    result = await session.execute(
        text(
            f"SELECT {_FACT_COLUMNS} FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    subject = result.mappings().first()
    if subject is None or subject["expired_at"] is not None:
        return None

    row = (
        await session.execute(
            text(_LATEST_SCAN_SQL),
            {"id": str(subject["id"]), "kind": CONTRADICTION_SCANNED},
        )
    ).first()
    if row is None:
        return None
    payload = row[0] or {}
    if payload.get("contradicted") is not True:
        return None

    dismissal = (
        await session.execute(
            text(_LATEST_DISMISSAL_SQL),
            {"id": str(subject["id"]), "kind": CONTRADICTION_DISMISSED},
        )
    ).first()
    if dismissal is not None and (dismissal[0], dismissal[1]) > (row[1], row[2]):
        return None

    counterpart_id = payload.get("counterpart_id")
    witness = payload.get("witness_origin")
    if not counterpart_id or not witness:
        return None

    counterpart = (
        await session.execute(
            text(_COUNTERPART_SQL),
            {"id": str(counterpart_id), "project": subject["project"]},
        )
    ).mappings().first()
    if counterpart is None:
        return None
    if not windows_overlap(
        subject["valid_at"],
        subject["invalid_at"],
        counterpart["valid_at"],
        counterpart["invalid_at"],
    ):
        return None

    if witness not in await _attributable_origins(session, counterpart["id"]):
        return None
    if witness in await _attributable_origins(session, subject["id"]):
        return None

    return ContradictionFinding(
        fact_id=str(subject["id"]),
        counterpart_id=str(counterpart["id"]),
        rule=RULE_SCANNED,
        witness_origin=witness,
        counterpart_subject=counterpart["subject_name"],
        counterpart_rel_type=counterpart["rel_type"],
        counterpart_object=counterpart["object_name"],
    )


ContradictionDetector = Callable[
    [AsyncSession, "UUID | str"], Awaitable[ContradictionFinding | None]
]

# Every detector whose verdict the veto composes. **A detector must not be
# plumbed past this tuple.** Recovery out of `disputed` is conjunctive — a fact
# is only adjudicated clean when every wired detector reports nothing — so a
# scan that reported through a side channel would let another's silence resolve
# a dispute it cannot see. Registering is what makes a detector's finding both
# able to open a dispute and required to keep it open.
#
# **One member, and the count is the ratified design rather than an omission**
# (doc 08 §4.2's 2026-08-08 amendment). `detect_scanned_contradiction` was the
# second member until then. Registering a model-backed detector here again puts
# a measured-0.88-precision instrument behind an unappealable veto, which is
# what three G-D runs measured and what the amendment forbids; the lawful place
# for such an arm is the ladder's contradiction-suspected review opener, where
# a false positive costs a glance rather than a near-permanent dispute.
CONTRADICTION_DETECTORS: tuple[ContradictionDetector, ...] = (
    detect_open_contradiction,
)


async def adjudicate_contradiction_finding(
    session: AsyncSession, fact_id: UUID | str
) -> ContradictionFinding | None:
    """The adjudication, returning *what* it found rather than *whether*.

    The first detector that finds one wins and the rest are not consulted, so
    the finding returned here is the one the verdict turned on and never an
    enumeration of every contradiction standing against the fact. That
    short-circuit is the veto's own shape — one contradiction is already
    absolute, so a second changes no outcome — and widening it would turn an
    O(1) adjudication into a full scan for a payload field. Callers that
    journal this must say which detector's finding they are carrying; the
    ladder does, through the finding's own ``rule``.
    """
    for detector in CONTRADICTION_DETECTORS:
        finding = await detector(session, fact_id)
        if finding is not None:
            return finding
    return None


async def adjudicate_contradiction(session: AsyncSession, fact_id: UUID | str) -> bool:
    """Is there an open contradiction against this fact? A definite verdict.

    ``True`` on the first detector that finds one; ``False`` only when every
    wired detector reported nothing. That conjunction is the whole meaning of
    ``False`` here, and it is why the ladder treats it as permission to leave
    ``disputed`` while treating "no detector ran" as a hold.

    Delegates rather than re-walking the registry, so the conjunction above is
    spelled exactly once: two loops over ``CONTRADICTION_DETECTORS`` could
    disagree about what a clean verdict means, and only one of them would be
    the one that ends a dispute.
    """
    return await adjudicate_contradiction_finding(session, fact_id) is not None

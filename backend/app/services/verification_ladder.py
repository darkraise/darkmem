"""The verification ladder: the promotion decision, and the knobs that bound it.

A fact's verification axis climbs ``candidate -> corroborated`` on
distinct-origin diversity. This module owns that decision and nothing else:
it never writes ``disputed`` (T2.04), never reaches ``confirmed`` (T2.05,
structurally refused by the repository), never schedules itself (T2.09), and
never applies demotion hysteresis (T2.46).

**Tier-C only (invariant 15).** Nothing in capture or retrieval may reach this
module. Reconciliation stays off the hot path, and the tempting failure is a
caller invoking the recompute inline so a fact promotes immediately. A
tree-wide source scan in ``tests/test_verification_ladder.py`` fails the build
if any module under ``backend/app`` outside the allowlist references it.

**The three thresholds are floors, not settings.** Doc 08 §4.1 fixes N = 2 when
the origins differ in source-kind or are >= 7 days apart, else 3. Those shipped
values are the conservative end: a config row may *tighten* them freely, but
loosening one requires a recorded G-C measurement (T2.40) listing that
parameter by name in the ``ladder_measurements`` row. An unbacked loosening is
clamped back to the floor with a warning rather than raising -- a bad row
degrades to the conservative bar instead of taking the recompute down, and the
conservative bar's failure is a delayed promotion, which the design accepts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.repositories.fact_sources import (
    FactSourceRepository,
    CORROBORATION_N_DEFAULT,
    CORROBORATION_N_DIVERSE,
    CORROBORATION_TIME_GAP_DAYS,
    OriginProfile,
)

logger = logging.getLogger(__name__)

LADDER_CONFIG_KEY = "verification_ladder"
LADDER_MEASUREMENTS_KEY = "ladder_measurements"

# The tuning task whose measurement is the only thing that may loosen a floor.
# Named in every clamp warning so the log line says what to do about it.
MEASUREMENT_TASK = "T2.40"


@dataclass(frozen=True)
class LadderConfig:
    """The three numbers the threshold rule needs, already validated.

    The defaults are the *same* values ``fact_sources`` computes
    ``required_origin_count`` from -- imported, never re-typed -- so the
    ladder's floor and the repository's constant cannot drift apart into two
    spellings of N.
    """

    n_default: int = CORROBORATION_N_DEFAULT
    n_diverse: int = CORROBORATION_N_DIVERSE
    time_gap_days: int = CORROBORATION_TIME_GAP_DAYS


# The two parameters that are counts of origins. A threshold of zero on either
# makes `k >= n` true for a fact with no sources; `time_gap_days` is a duration
# and carries no such hazard, so the absolute floor applies only to these.
_ORIGIN_COUNT_PARAMS = frozenset({"n_default", "n_diverse"})

# Every parameter's floor is its shipped default. Spelled as a mapping rather
# than read off LadderConfig() so that "what ships" and "what may not be gone
# below" stay one statement: a future default change moves the floor with it.
LADDER_FLOORS: dict[str, int] = {
    "n_default": CORROBORATION_N_DEFAULT,
    "n_diverse": CORROBORATION_N_DIVERSE,
    "time_gap_days": CORROBORATION_TIME_GAP_DAYS,
}


async def get_ladder_measurements(session: AsyncSession) -> frozenset[str]:
    """Which ladder parameters carry a recorded G-C measurement.

    Modelled on ``feature_flags.get_measured_flags``: a ``config`` row that
    nothing in this codebase writes, whose only intended writer is the
    gate-clearing process recording a ledger entry. Empty by default.

    Permission is **per parameter**, never blanket. A row that merely exists
    unlocks nothing; only the parameters it names by name are honoured below
    their floor. Blanket permission would let one measured parameter carry
    three loosened ones past the gate.
    """
    result = await session.execute(
        select(Config).where(Config.key == LADDER_MEASUREMENTS_KEY)
    )
    row = result.scalar_one_or_none()
    if not row or not isinstance(row.value, dict):
        return frozenset()
    measured = row.value.get("measured", [])
    if not isinstance(measured, list):
        return frozenset()
    return frozenset(name for name in measured if name in LADDER_FLOORS)


async def get_ladder_config(session: AsyncSession) -> LadderConfig:
    """The effective thresholds: merge over defaults, validate, clamp.

    The row is operator-edited with no schema in front of it, so every
    malformed shape degrades rather than raising: an unknown key is ignored
    with a warning naming it, a non-integer value falls back to its default,
    and a value below its floor is clamped unless a measurement names that
    parameter.
    """
    result = await session.execute(select(Config).where(Config.key == LADDER_CONFIG_KEY))
    row = result.scalar_one_or_none()
    raw = row.value if row and isinstance(row.value, dict) else {}

    measured = await get_ladder_measurements(session) if raw else frozenset()

    for key in raw:
        if key not in LADDER_FLOORS:
            logger.warning(
                "%s config row carries unknown key %r; ignoring. Known keys: %s",
                LADDER_CONFIG_KEY,
                key,
                sorted(LADDER_FLOORS),
            )

    values: dict[str, int] = {}
    for name, floor in LADDER_FLOORS.items():
        if name not in raw:
            values[name] = floor
            continue
        candidate = raw[name]
        # bool is an int subclass, and True would silently read as 1 -- a
        # loosening that looks like a typo but clamps like a decision.
        if isinstance(candidate, bool) or not isinstance(candidate, int):
            logger.warning(
                "%s.%s is %r, not an integer; falling back to the default %d",
                LADDER_CONFIG_KEY,
                name,
                candidate,
                floor,
            )
            values[name] = floor
            continue
        if name in _ORIGIN_COUNT_PARAMS and candidate < 1:
            # A measured parameter is otherwise honoured verbatim, and N = 0
            # would make `k >= n` true for a fact with **no sources at all** —
            # promotion on nothing. The measurement gate trusts T2.40's writer
            # about *how far* to loosen, never about whether the threshold may
            # vanish, so this bound sits outside the gate and applies even to a
            # measured parameter. It covers the two origin-count parameters
            # only: `time_gap_days = 0` is degenerate (the gate always fires)
            # but still lands on `n_diverse`, so it cannot promote a
            # zero-source fact and stays governed by its floor.
            logger.warning(
                "%s.%s=%d is below the absolute minimum of 1; raising to 1. "
                "An origin threshold of zero would promote a fact with no sources.",
                LADDER_CONFIG_KEY,
                name,
                candidate,
            )
            values[name] = 1
            continue
        if candidate < floor and name not in measured:
            logger.warning(
                "%s.%s=%d is below its floor %d and no %s measurement lists it; "
                "clamping to %d. Loosening a ladder threshold requires a recorded "
                "measurement, not an edit.",
                LADDER_CONFIG_KEY,
                name,
                candidate,
                floor,
                MEASUREMENT_TASK,
                floor,
            )
            values[name] = floor
            continue
        values[name] = candidate

    # The ordering invariant is NOT unlockable by measurement. n_default is the
    # ungated bar and n_diverse the gated one, so n_default < n_diverse inverts
    # the ladder: firing a gate would *raise* N, and corroborating evidence
    # would make promotion harder. No measurement can make that coherent, so
    # unlike the three floors this clamps unconditionally.
    if values["n_default"] < values["n_diverse"]:
        logger.warning(
            "%s has n_default=%d below n_diverse=%d, which inverts the ladder; "
            "raising n_default to %d. This clamp is not unlockable by measurement.",
            LADDER_CONFIG_KEY,
            values["n_default"],
            values["n_diverse"],
            values["n_diverse"],
        )
        values["n_default"] = values["n_diverse"]

    return LadderConfig(**values)


# ─────────────────────────── the decision ───────────────────────────

# The machine's reachable targets. `confirmed` is a human's floor above the
# machine's ceiling (T2.05) and `disputed` is the veto's verdict (T2.04);
# neither is representable here, and the runtime assertions in the test suite
# check that, because Python does not enforce annotations.
MachineTarget = Literal["candidate", "corroborated"]
Outcome = Literal["promote", "demote", "hold"]

# The default contradiction verdict: "no detector exists yet", not "adjudicated
# and found clean". T2.04 builds the detector; naming the absence keeps a
# caller from reading a stub's silence as a finding.
NO_DETECTOR = False


@dataclass(frozen=True)
class LadderDecision:
    """What the ladder concluded, and every input that produced it.

    Returned whole rather than applied silently: T2.06 wires this into the
    journal payload as the transition's evidence, and G-C's metrics are
    computed from that journal, so a decision that cannot explain itself is a
    transition G-C cannot count.
    """

    fact_id: str
    current_status: str
    target_status: str
    outcome: Outcome
    origin_count: int
    required_n: int
    gate_fired: str
    source_kinds: tuple[str, ...]
    contradiction_blocked: bool
    confidence: float


def compute_confidence(*, origin_count: int, required_n: int, gate_fired: str) -> float:
    """The aggregated support estimate doc 04 §8.3 binds to the status.

    The corpus fixes the *properties* -- aggregated, recomputed alongside
    ``verification_status``, never a single-source guess -- but no formula, so
    the formula is stated in T2.03's plan §3 D4 and pinned by exact-value
    vectors rather than by properties alone: four properties are all survived
    by a coefficient typo.

        support    = min(K, N) / N
        confidence = min(0.90, 0.40 + 0.40*support + 0.10*(gate fired))

    Capped at 0.90 because the machine never claims certainty -- the badge's
    honest claim is "asserted by K distinct origins of kinds [...], no known
    contradiction, as of T", never "true".

    **Contradiction deliberately does not enter this number.** A
    contradiction-blocked hold with K >= N and a fired gate carries 0.90.
    That is intended: confidence is *support*, while a dispute is a fact about
    adjudication and lives on the verification and ``review_state`` surfaces
    T2.04 owns. Stated because "high confidence on a blocked fact" reads as a
    bug to anyone who has not read this paragraph.
    """
    if required_n <= 0:  # defensive: the clamps make this unreachable
        return 0.40
    support = min(origin_count, required_n) / required_n
    raw = 0.40 + 0.40 * support + 0.10 * (1.0 if gate_fired != "none" else 0.0)
    return min(0.90, raw)


def decide(
    fact_id: str,
    current_status: str,
    profile: OriginProfile,
    config: LadderConfig,
    *,
    open_contradiction: bool = NO_DETECTOR,
) -> LadderDecision:
    """Promotion, demotion or hold -- a pure function of the four inputs.

    **No I/O, no session, and no clock.** The time gate reads
    ``OriginProfile.max_cross_origin_gap``, which is computed purely from
    stored timestamps relative to *each other*; reading the wall clock here
    would make a replay of the same inputs produce a different answer as the
    calendar moves, which is what "reproducible on replay" forbids.

    ``open_contradiction`` is a keyword on purpose. T2.60's sibling blocker --
    a newer REPLACES-family / supersession signal over the fact's live memory
    sources -- slots in beside it as a purely additive keyword when that task
    lands. It is deliberately *not* added now: it would have no provider, and
    a zero-writer input presented as substrate is the thing invariant 23
    forbids (ruling, 2026-07-29).
    """
    k = profile.origin_count
    n = profile.required_origin_count_for(
        n_diverse=config.n_diverse,
        n_default=config.n_default,
        time_gap_days=config.time_gap_days,
    )
    gate = profile.gate_fired_for(time_gap_days=config.time_gap_days)
    confidence = compute_confidence(origin_count=k, required_n=n, gate_fired=gate)

    def settled(target: str, outcome: Outcome, *, blocked: bool = False) -> LadderDecision:
        return LadderDecision(
            fact_id=fact_id,
            current_status=current_status,
            target_status=target,
            outcome=outcome,
            origin_count=k,
            required_n=n,
            gate_fired=gate,
            source_kinds=profile.source_kinds,
            contradiction_blocked=blocked,
            confidence=confidence,
        )

    # A human ratified this fact. The machine never moves it in either
    # direction -- not down on a lost origin, not sideways on a contradiction.
    # Confidence is still refreshed, because the human's row is itself a
    # dominant origin and the support estimate stays meaningful.
    if current_status == "confirmed":
        return settled("confirmed", "hold")

    # Entry into and recovery out of `disputed` are both T2.04's transitions
    # (recorded in E2's amendment log, 2026-07-29). Holding unconditionally is
    # what stops the NO_DETECTOR stub from "resolving" a real dispute into
    # `corroborated` the first time this runs over one.
    if current_status == "disputed":
        return settled("disputed", "hold")

    if open_contradiction:
        return settled(current_status, "hold", blocked=True)

    if k >= n:
        if current_status == "corroborated":
            return settled("corroborated", "hold")
        return settled("corroborated", "promote")

    # Below N. Demotion is immediate here; doc 08 §4.3's hysteresis and the
    # `under-sourced` label are T2.46's, interposed at the applier on this
    # first-class `demote` outcome without touching this function.
    if current_status == "corroborated":
        return settled("candidate", "demote")
    return settled("candidate", "hold")


# ─────────────────────────── the applier ───────────────────────────


async def recompute_fact(
    session: AsyncSession,
    fact_id: UUID | str,
    *,
    open_contradiction: bool = NO_DETECTOR,
) -> LadderDecision:
    """Recompute one fact's verification status, and return why.

    The per-fact primitive. The **job** that finds which facts to call this on
    -- draining ``sources_changed`` past a watermark, deduping, scheduling --
    is T2.09's; this function neither reads events nor registers itself.

    **This is the sole journaller of verification transitions**, which is the
    hand-off ``set_verification_status`` was written anticipating: the only
    write path here is that repository method, so exactly one ``verified``
    event exists per transition and G-C cannot double-count one.

    A ``fact_id`` with no row returns a hold that writes nothing. The drain
    that will call this races deletion by construction, so raising would turn
    an ordinary race into a failed job.
    """
    config = await get_ladder_config(session)
    profile = await FactSourceRepository(session).origin_profile(fact_id)

    # FOR UPDATE, and it is load-bearing rather than defensive. Without it the
    # row is unlocked between this read and the applier's write, so a
    # concurrently committed `disputed` verdict (T2.04's veto shape) gets
    # overwritten: the decision was taken on a `candidate` the row no longer
    # holds, and the applier journals `disputed -> corroborated` — the
    # contradiction-resolved transition doc 08 §4 reserves for T2.04, emitted by
    # a machine with no detector. Locking from read through write is what makes
    # the decision-layer disputed-hold survive concurrency; today no production
    # caller of either side exists, but T2.04 and T2.09 will run concurrently.
    row = await session.execute(
        text(
            "SELECT verification_status FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid) FOR UPDATE"
        ),
        {"id": str(fact_id)},
    )
    current = row.scalar_one_or_none()
    if current is None:
        logger.debug("recompute_fact: no knowledge_triples row for id %s", fact_id)
        return LadderDecision(
            fact_id=str(fact_id),
            current_status="missing",
            target_status="missing",
            outcome="hold",
            origin_count=0,
            required_n=config.n_default,
            gate_fired="none",
            source_kinds=(),
            contradiction_blocked=False,
            confidence=0.0,
        )

    decision = decide(
        str(fact_id),
        current,
        profile,
        config,
        open_contradiction=open_contradiction,
    )

    repo = KnowledgeTripleRepository(session)
    # A held fact writes confidence alone: `confirmed` cannot be passed its own
    # status back (the repository refuses it before any read), and a status
    # write that changes nothing would only risk a phantom journal row.
    status_to_write = (
        decision.target_status if decision.target_status != decision.current_status else None
    )
    await repo.set_verification_status(
        fact_id, status_to_write, confidence=decision.confidence
    )
    return decision

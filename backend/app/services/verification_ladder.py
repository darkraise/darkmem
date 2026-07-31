"""The verification ladder: the promotion decision, and the knobs that bound it.

A fact's verification axis climbs ``candidate -> corroborated`` on
distinct-origin diversity, and is vetoed sideways to ``disputed`` by a single
non-echo contradiction (T2.04). This module owns that decision and nothing else:
it never reaches ``confirmed`` (T2.05, structurally refused by the repository),
never schedules itself (T2.09), and never applies demotion hysteresis (T2.46).
It also owns the review queue's ``review_state`` flag, which is *derived* from
the decision rather than assigned by each opener in turn — the ruling and what
it binds T2.46 and T2.22 to is in ``derive_review_state``.

**The veto is absolute and reads no configuration.** However many origins
corroborate a fact, one contradiction beats them (doc 08 §4.2) — not a weight,
not a score, not a threshold. The three thresholds below govern *promotion*
only; none of them is on the veto's path, and
``tests/test_contradiction_veto.py`` fails the build if one becomes so.

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
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories.knowledge_triples import (
    REVIEW_STATE_OPEN,
    KnowledgeTripleRepository,
)
from app.repositories.fact_sources import (
    FactSourceRepository,
    CORROBORATION_N_DEFAULT,
    CORROBORATION_N_DIVERSE,
    CORROBORATION_TIME_GAP_DAYS,
    OriginProfile,
)
from app.services.contradiction_veto import adjudicate_contradiction
from app.services.supersession_hold import adjudicate_supersession_hold

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
        # The floor clamp runs FIRST, and the ordering matters. An earlier
        # revision put the absolute >= 1 bound ahead of this branch and
        # `continue`d past it, so an unmeasured `n_default: 0` never reached
        # its floor: it became 1, then the ordering clamp lifted it to 2, and
        # a two-same-kind-same-day-origin fact promoted where the floor holds
        # at 3 — an operator typo manufacturing exactly the counterfeit
        # corroboration D3 exists to prevent. Every floor is >= 1, so clamping
        # here already satisfies the absolute bound for the unmeasured case.
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
        # Only a *measured* value can still be under 1 by this point. The
        # measurement gate rules how far a threshold may loosen, never whether
        # it may vanish: N = 0 makes `k >= n` true for a fact with no sources
        # at all. Origin-count parameters only — `time_gap_days = 0` is
        # degenerate (the gate always fires) but still lands on `n_diverse`,
        # so it cannot promote a zero-source fact.
        if name in _ORIGIN_COUNT_PARAMS and candidate < 1:
            logger.warning(
                "%s.%s=%d is below the absolute minimum of 1; raising to 1. "
                "An origin threshold of zero would promote a fact with no "
                "sources, which no %s measurement can authorise.",
                LADDER_CONFIG_KEY,
                name,
                candidate,
                MEASUREMENT_TASK,
            )
            values[name] = 1
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
# machine's ceiling (T2.05) and stays unrepresentable here; `disputed` became
# reachable with T2.04's veto, but only through `open_contradiction` — never
# off the origin count. The runtime assertions in the test suite check both,
# because Python does not enforce annotations.
MachineTarget = Literal["candidate", "corroborated", "disputed"]
Outcome = Literal["promote", "demote", "hold", "dispute", "recover"]

# The contradiction verdict is three-valued, and the third value is the point.
# `None` is "no detector reported", which is not the same claim as `False`
# ("every wired detector adjudicated this fact and found nothing"). Collapsing
# them is what would let a machine with no detector behind it journal
# `disputed -> corroborated`: the disputed hold below turns on this distinction,
# so only an affirmative adjudication can end a dispute.
ContradictionVerdict = bool | None
NO_DETECTOR: ContradictionVerdict = None


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
    # T2.60. Defaulted so a construction site that predates the blocker keeps
    # reporting the unblocked answer rather than failing to build, which is the
    # same extensibility T2.46's hysteresis field will need. It means exactly
    # "this decision withheld a promotion because a newer supersession signal
    # stands over a memory source", never "a signal exists somewhere": the
    # metric that reads it counts blocked promotions, so a flag set on a
    # decision that was never going to promote would inflate that count.
    supersession_blocked: bool = False


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
    open_contradiction: ContradictionVerdict = NO_DETECTOR,
    supersession_blocked: bool = False,
) -> LadderDecision:
    """Promotion, demotion, dispute, recovery or hold -- a pure function.

    **No I/O, no session, and no clock.** The time gate reads
    ``OriginProfile.max_cross_origin_gap``, which is computed purely from
    stored timestamps relative to *each other*; reading the wall clock here
    would make a replay of the same inputs produce a different answer as the
    calendar moves, which is what "reproducible on replay" forbids.

    ``open_contradiction`` is the veto, and it is **absolute**: no branch below
    consults ``config`` before honouring it, and there is no arithmetic between
    the verdict and the outcome. ``k`` and ``n`` are still computed because the
    decision record must report the support it overrode, not because they can
    change the answer.

    ``supersession_blocked`` is spec §2.1 condition 4's other half (T2.60, and
    the 2026-07-29 ruling that restored it after doc 08 dropped it by drift):
    a newer REPLACES-family signal standing over one of the fact's memory
    sources. It is adjudicated in ``recompute_fact`` for the same reason the
    contradiction verdict is -- it needs a session this function must not have
    -- and ``supersession_hold`` holds the predicate and its argument. Unlike
    the contradiction verdict it is a plain boolean rather than a tri-state:
    the third value exists there because ``False`` is permission to *leave*
    ``disputed``, and this signal resolves nothing.

    **It blocks and only blocks.** It is consulted after the ``confirmed``
    hold, after the veto and after the already-``corroborated`` hold, so it
    can never write ``disputed`` and can never demote. Its two branches are
    the two doors into ``corroborated``: the ordinary promotion, and the
    recovery out of ``disputed`` at or above the bar.

    **The T2.06 ruling this discharges (2026-07-31).** T2.06 justified leaving
    ordinary holds unjournaled by arguing they carry nothing a G-C metric
    reads: an unblocked candidate below its bar "was never eligible, excluded
    from the promotion-rate denominator by construction, not by omission".
    This blocker breaks that equivalence by construction, because it is
    precisely a meets-bar-but-holds path. The ruling bound the resolution
    rather than leaving it open -- carry a ``supersession_blocked`` field and
    journal it exactly the way ``contradiction_blocked`` is journaled (the
    OR-branch in ``KnowledgeTripleRepository.set_verification_status``), never
    ruling the fact ineligible, "because the alternative lets a widening block
    silently inflate the promotion rate with no trace". Both halves are done.
    The restated eligibility equivalence and the denominator argument the
    metrics runner must implement are in ``supersession_hold``'s module
    docstring, beside the predicate they describe.
    """
    k = profile.origin_count
    n = profile.required_origin_count_for(
        n_diverse=config.n_diverse,
        n_default=config.n_default,
        time_gap_days=config.time_gap_days,
    )
    gate = profile.gate_fired_for(time_gap_days=config.time_gap_days)
    confidence = compute_confidence(origin_count=k, required_n=n, gate_fired=gate)

    def settled(
        target: str,
        outcome: Outcome,
        *,
        blocked: bool = False,
        superseded: bool = False,
    ) -> LadderDecision:
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
            supersession_blocked=superseded,
        )

    # A human ratified this fact. The machine never moves it in either
    # direction -- not down on a lost origin, not sideways on a contradiction.
    # Confidence is still refreshed, because the human's row is itself a
    # dominant origin and the support estimate stays meaningful.
    if current_status == "confirmed":
        return settled("confirmed", "hold")

    # The veto, before every count. One non-echo contradiction beats any number
    # of corroborations (doc 08 §4.2), so it is checked ahead of the threshold
    # rule rather than weighed against it -- there is no arithmetic on this path
    # for a config row to reach.
    if open_contradiction is True:
        if current_status == "disputed":
            return settled("disputed", "hold", blocked=True)
        return settled("disputed", "dispute", blocked=True)

    # Recovery out of `disputed`, which is T2.04's transition too (recorded in
    # E2's amendment log, 2026-07-29). It needs an *affirmative* clean verdict:
    # `NO_DETECTOR` still holds unconditionally, so a caller that ran no
    # detector cannot resolve a dispute by silence -- the property T2.03's
    # unconditional hold protected, now protected by the verdict's third value
    # instead. Recovery then re-enters the ordinary rule rather than jumping
    # straight to `corroborated`: a fact that lost its origins while disputed
    # has had its contradiction resolved, not its support restored.
    if current_status == "disputed":
        if open_contradiction is None:
            return settled("disputed", "hold")
        # Recovery lands on `corroborated` only when it would have promoted, so
        # the blocker applies here for the same reason it applies below: leaving
        # `disputed` at or above the bar *is* a promotion, and letting one
        # through the recovery door would make the block depend on whether the
        # fact happened to be disputed first. Recovering to `candidate` is the
        # branch's own below-bar outcome, not a demotion this blocker invented.
        if k >= n and supersession_blocked:
            return settled("candidate", "recover", superseded=True)
        return settled("corroborated" if k >= n else "candidate", "recover")

    if k >= n:
        if current_status == "corroborated":
            return settled("corroborated", "hold")
        # Checked *after* the already-corroborated hold, and the order is the
        # whole of clause 3. This blocker withholds promotions; it never demotes
        # a fact that already holds the badge, so a corroborated fact leaves by
        # the branch above with the flag unset and no status write. Reaching
        # here means the fact is below `corroborated` and met its bar -- the
        # meets-bar-but-holds path T2.06's ruling requires be journaled.
        if supersession_blocked:
            return settled(current_status, "hold", superseded=True)
        return settled("corroborated", "promote")

    # Below N. Demotion is immediate here; doc 08 §4.3's hysteresis and the
    # `under-sourced` label are T2.46's, interposed at the applier on this
    # first-class `demote` outcome without touching this function.
    if current_status == "corroborated":
        return settled("candidate", "demote")
    return settled("candidate", "hold")


# ────────────────────── the review queue's open flag ──────────────────────

ReviewOpener = Callable[[LadderDecision], bool]


def _dispute_opens_review(decision: LadderDecision) -> bool:
    """Doc 08 §4.3's flowchart node reads "set ``disputed``, ``review_state``
    open" — one node, so this predicate is the veto's outcome and nothing else.

    It keys off ``target_status`` rather than ``outcome`` on purpose: the
    ``dispute`` outcome and the ``contradiction_blocked`` hold both land on
    ``disputed``, and a standing dispute re-confirmed across a recompute cycle
    must stay queued. Keying off ``outcome == "dispute"`` would silently make
    the re-confirm a no-op, and the flag would then depend on which cycle the
    human happened to look at.
    """
    return decision.target_status == "disputed"


# Every condition that puts a fact on the review queue. **T2.46's
# ``under-sourced`` hysteresis joins this tuple; it must not be plumbed past
# it**, exactly as ``CONTRADICTION_DETECTORS`` binds T2.11. Registering is what
# makes an opener's condition both able to open the queue and *required* to
# keep it open.
REVIEW_OPENERS: tuple[ReviewOpener, ...] = (_dispute_opens_review,)


def derive_review_state(decision: LadderDecision) -> str | None:
    """Whether this fact belongs on the review queue — derived, never assigned.

    **The ruling (T2.62, 2026-07-31): ``review_state`` is a value recomputed
    from the fact's current conditions at this one point, not a flag each
    opener sets and clears in whatever order it happens to run.** Doc 08 §6
    gives the column three independent openers — a disputed fact (§4.2, this
    one), an under-sourced fact held in hysteresis (§4.3, T2.46), and an
    ungrounded article (doc 09, a *different table* and so not a member of
    ``REVIEW_OPENERS``) — plus a human clearer. On disk it is a bare nullable
    TEXT column whose only index is partial on the literal ``'open'``, so it
    has no room to record *which* opener owns it. Several writers over one bit
    with no owner field is how a fact that is disputed **and** under-sourced
    silently leaves the queue when only the dispute resolves: nothing errors,
    and the human simply never sees it again.

    Deriving makes precedence a property that can be stated and tested instead
    of an emergent property of write order: **the clear is the absence of every
    opener, never the negation of one.** Adding an opener is appending a
    predicate here, not adding a writer.

    The derivation is **total** — a definite value for every decision,
    including ``confirmed``, on which no opener fires because doc 08 §4.4 makes
    a ratified fact immune to both the veto and demotion. A partial derivation
    ("no opinion on this branch") would reintroduce exactly the ownership
    ambiguity this ruling exists to remove.

    **What T2.46 must do to stay consistent.** Carry its hysteresis state as a
    field on ``LadderDecision`` — the shape T2.06's ruling already prescribes
    for T2.60's ``supersession_blocked`` — and register a predicate over it
    here. It must not write ``review_state`` itself. And it must not put the
    ``under-sourced`` *label* in this column: the queue predicate and the
    partial index are both the literal ``'open'``, so a row labelled
    ``'under-sourced'`` is a row that has silently left the queue, which is the
    very failure this ruling exists to forbid. Doc 08 §4.3 already names the
    marker that carries the label — ``demotion_pending_since``, §9's one small
    schema amendment and T2.46's to land — and ``demotion_pending_since IS NOT
    NULL`` is simultaneously the label the UI renders and the predicate this
    tuple wants. So the companion column this ruling would otherwise need
    already has an owner, and T2.62 needs no schema change of its own.

    **What T2.22 must do to stay consistent.** Read the column; do not ship a
    bare "clear review_state" action on it. A bare clear does not survive the
    next recompute (below), and a control whose effect is silently undone
    minutes later is worse than no control.

    **What T2.24 must do to stay consistent.** Its stale-dispute decay cannot
    be expressed as a ``review_state`` value at all: the repository refuses any
    literal other than ``'open'``, and the unconditional open would re-stomp a
    decayed marker on every recompute while the dispute still stands. That is
    the correct outcome rather than a limitation — doc 08 §6 makes the decay a
    change of *priority*, leaving the fact ``disputed``, on the queue and served
    labelled with both sides — so the decay belongs on the ranking side T2.24
    owns, never on this column.

    **A human's bare clear reopens, and that is the correct answer.** A
    derivation cannot honour one: the next recompute reopens the flag while the
    dispute still stands. Doc 08 §6 names three human verbs and every one of
    them *changes a condition* — ratify (``confirmed``, §4.4, on which no
    opener fires), re-ground (adds origins), edit (removes the contradiction) —
    so each is honoured by derivation with no special case at all. What §6 does
    **not** give the human is a bare dismiss, and the reason sits in the same
    paragraph: the "stop showing me this" affordance is the staleness decay
    (T2.24), which drops a dispute off the *active* queue by priority while
    leaving it ``disputed`` and served labelled with both sides. Making a bare
    clear sticky would duplicate that affordance with strictly worse semantics
    — it would remove the fact from the queue *and* leave no trace of why —
    which is the silencing invariant 14 forbids.

    Three alternatives were considered and rejected.

    *Teach the clear to skip values it did not write.* With no owner field the
    only discriminator is the value itself, and the queue predicate pins every
    opener to the same literal ``'open'``, so "mine" and T2.46's are
    indistinguishable on disk. It cannot be implemented, only approximated, and
    an approximated precedence rule is precisely the guard that reads stronger
    than it is.

    *Open-only, never clear.* It satisfies the no-stomp requirement trivially
    and fails the recovery requirement, and it turns the queue into an
    append-only backlog only a human can drain — the throughput bottleneck doc
    08 §6 chose a self-pruning status flag to avoid.

    *A companion ``review_reasons TEXT[]``.* It is the right shape if the
    column ever has to carry *why*, and it is not needed for that: each opener
    is derivable from state the fact already holds, so the reason set would be
    a denormalised cache of a computation that several writers would then have
    to keep honest — and the derivation is the cheaper way to get the same
    guarantee. It is also a baseline regeneration, which serialises through one
    owner per epic.
    """
    if any(opener(decision) for opener in REVIEW_OPENERS):
        return REVIEW_STATE_OPEN
    return None


# ─────────────────────────── the applier ───────────────────────────


async def recompute_fact(
    session: AsyncSession,
    fact_id: UUID | str,
    *,
    open_contradiction: ContradictionVerdict = NO_DETECTOR,
    supersession_blocked: bool | None = None,
) -> LadderDecision:
    """Recompute one fact's verification status, and return why.

    The per-fact primitive. The **job** that finds which facts to call this on
    -- draining ``sources_changed`` past a watermark, deduping, scheduling --
    is T2.09's; this function neither reads events nor registers itself.

    The contradiction verdict is **adjudicated here**, on this side of the
    purity boundary, because it needs the session ``decide`` must not have. A
    caller may pass a verdict to override the scan (a replay re-deciding
    recorded inputs); leaving it at ``NO_DETECTOR`` runs every wired detector
    under the same lock and transaction as the status write, so the verdict
    cannot be taken against a row the applier no longer holds.

    T2.60's supersession blocker is adjudicated on the same side, for the same
    reason and inside the same lock: its predicate reads ``fact_sources`` and
    ``memories``, and a signal taken outside the ``FOR UPDATE`` window could
    describe provenance the applier no longer holds. ``None`` means "scan
    here"; an explicit boolean overrides it, which is what lets a replay
    re-decide recorded inputs without a live graph.

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

    verdict = open_contradiction
    if verdict is NO_DETECTOR:
        verdict = await adjudicate_contradiction(session, fact_id)

    blocked = supersession_blocked
    if blocked is None:
        blocked = await adjudicate_supersession_hold(session, fact_id)

    decision = decide(
        str(fact_id),
        current,
        profile,
        config,
        open_contradiction=verdict,
        supersession_blocked=blocked,
    )

    repo = KnowledgeTripleRepository(session)
    # A held fact writes confidence alone: `confirmed` cannot be passed its own
    # status back (the repository refuses it before any read), and a status
    # write that changes nothing would only risk a phantom journal row. The
    # repository still journals on `contradiction_blocked` alone (a reconfirmed
    # `disputed -> disputed` hold), so the evidence rides every call regardless
    # of whether this particular decision carries a status change.
    status_to_write = (
        decision.target_status if decision.target_status != decision.current_status else None
    )
    # `review_state` goes down with the status, in that method's single UPDATE
    # and under the FOR UPDATE taken above, so `disputed`-but-unqueued is not a
    # state anything can observe. It is passed on *every* call, including the
    # holds that write no status: the flag is derived from current conditions,
    # so a branch that declined to pass it would leave a stale queue entry
    # behind exactly where the derivation is the only thing that could clear it.
    await repo.set_verification_status(
        fact_id,
        status_to_write,
        confidence=decision.confidence,
        review_state=derive_review_state(decision),
        outcome=decision.outcome,
        origin_count=decision.origin_count,
        required_n=decision.required_n,
        gate_fired=decision.gate_fired,
        source_kinds=decision.source_kinds,
        contradiction_blocked=decision.contradiction_blocked,
        supersession_blocked=decision.supersession_blocked,
    )
    return decision

"""The verification ladder: the promotion decision, and the knobs that bound it.

A fact's verification axis climbs ``candidate -> corroborated`` on
distinct-origin diversity, and is vetoed sideways to ``disputed`` by a single
non-echo contradiction (T2.04). This module owns that decision and nothing else:
it never reaches ``confirmed`` (T2.05, structurally refused by the repository)
and never schedules itself (T2.09). It also owns the review queue's
``review_state`` flag, which is *derived* from the decision rather than
assigned by each opener in turn — the ruling and what it binds T2.22 to is in
``derive_review_state``.

**Demotion carries hysteresis, and the decision layer does not** (doc 08 §4.3,
T2.46). ``decide`` still rules a below-N ``corroborated`` fact a ``demote``,
unconditionally and with no state to consult; ``apply_demotion_hysteresis``
then holds that demotion for ``verification_demote_grace_cycles`` consecutive
cycles, labelling the fact ``under-sourced`` in the meantime. The label is an
overlay on a still-``corroborated`` row — ``demotion_pending_since IS NOT
NULL``, never a fifth ``verification_status``, which the database CHECK would
refuse anyway — and it is **served, never withheld**: no path filters a fact
out on the marker, and no path drops the row while keeping the label off it.

**Carrying the label is per-surface, and the list is finite** (corrected
2026-08-03; the earlier claim here — "the marker rides ``_COLUMNS``, so every
fact read path carries it" — was broader than the code, and two serving
surfaces did not carry it). ``_COLUMNS`` covers the repository reads (``get``,
``get_live``, ``list_live``, ``as_of``), but a surface that hand-enumerates its
own projection has to name the marker itself: today that is
``facts_read._base_item`` with ``FactListItem`` behind it (doc 13 §5.1's Facts
tab, where §5.3's caution overlay renders), ``facts_channel``'s row payload,
and the review queue's item. Every *other* reader of ``knowledge_triples``
selects a narrow projection for an internal decision — adjudication, ranking,
counting — and serves no label at all. **A new surface that enumerates its own
columns is a new place the label can go missing**, and it goes missing
silently, because nothing is withheld: the fact arrives looking healthy.

**The veto is absolute and reads no configuration.** However many origins
corroborate a fact, one contradiction beats them (doc 08 §4.2) — not a weight,
not a score, not a threshold. The three thresholds below govern *promotion*
only; none of them is on the veto's path, and
``tests/test_contradiction_veto.py`` fails the build if one becomes so.

**Two contradiction signals, and only one of them is that veto** (doc 08 §4.2's
2026-08-08 amendment, T2.109). ``open_contradiction`` carries the deterministic
arm's verdict and moves the fact to ``disputed``. The Tier-C model scan's
journalled verdict arrives on a *separate* parameter, ``contradiction_suspected``,
and reaches ``decide`` only to be recorded on the decision and read by the
contradiction-suspected review opener: it changes no rung, no badge and no
outcome. Routing it into ``open_contradiction`` instead is the one mistake this
split exists to make unavailable — it would put a measured-0.88-precision
instrument behind an unappealable veto, which is the wiring three G-D runs
measured and the amendment removed.

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
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories.knowledge_triples import (
    REVIEW_STATE_OPEN,
    UNSET_DEMOTION_PENDING,
    UNSET_SUSPICION,
    ContradictionSuspicion,
    DemotionPending,
    KnowledgeTripleRepository,
)
from app.repositories.fact_sources import (
    FactSourceRepository,
    OriginProfile,
)
from app.services.contradiction_veto import (
    ContradictionFinding,
    adjudicate_contradiction_finding,
    detect_scanned_contradiction,
)
from app.services.supersession_hold import adjudicate_supersession_hold

logger = logging.getLogger(__name__)

# The threshold knobs live in `ladder_config` — resolution, floors, clamps and
# the report a settings surface renders. They are re-exported here because this
# module is where every caller has always imported them from, and because the
# split is about which module a *config door* has to name, not about hiding
# them from the decision that uses them. See that module's docstring for why a
# settings route may not simply be allowlisted into this one.
from app.services.ladder_config import (  # noqa: E402,F401  (re-exports)
    LADDER_CONFIG_KEY,
    LADDER_FLOORS,
    LADDER_MEASUREMENTS_KEY,
    MEASUREMENT_TASK,
    LadderConfig,
    LadderParamReport,
    LadderReport,
    get_ladder_config,
    get_ladder_measurements,
    resolve_ladder,
)


# Doc 08 §4.3's demotion grace, in *consecutive recompute cycles*. Its own
# `config` row rather than a fourth key on `verification_ladder`'s, because
# that row is the promotion thresholds and its clamp is a floor: a value
# below the shipped default is refused without a measurement. This knob's
# conservative direction is the opposite one — fewer cycles demotes sooner,
# which under-claims — so routing it through that machinery would clamp it
# backwards. Doc 17 §5.1 puts it under the same *tuning protocol*, which is a
# statement about how an operator arrives at a number, not about which way
# the runtime refuses one.
DEMOTE_GRACE_CONFIG_KEY = "verification_demote_grace_cycles"
DEMOTE_GRACE_VALUE_KEY = "cycles"

# Doc 08 §9's shipped value: one full cycle of persistence under N.
DEMOTE_GRACE_DEFAULT = 1

# A ceiling, not a tuning range. Grace has no natural upper bound in the
# corpus, and an operator typo of one extra digit would hold a fact's
# `corroborated` rung indefinitely on evidence that no longer supports it.
# The `under-sourced` label keeps that honest while the window runs, which is
# why an unbounded hold is a bounded harm rather than a silent lie — but the
# rung must still eventually fall, so the value is clamped rather than
# trusted.
DEMOTE_GRACE_MAX = 100

async def get_demote_grace_cycles(session: AsyncSession) -> int:
    """How many consecutive recompute cycles a demotion is held for.

    Same degrade-never-raise posture as ``get_ladder_config``: the row is
    operator-edited with no schema in front of it, so a malformed shape falls
    back to the shipped default with a warning rather than taking the
    recompute down.

    ``0`` is a legitimate value and means "no hysteresis" — the demotion
    applies on the cycle that detects it, which is the pre-T2.46 behaviour and
    the conservative end of this knob. It is reachable deliberately, so a
    deployment that measures hysteresis costing more than it saves can turn it
    off without a code change.
    """
    result = await session.execute(
        select(Config).where(Config.key == DEMOTE_GRACE_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    raw = row.value if row and isinstance(row.value, dict) else {}
    if DEMOTE_GRACE_VALUE_KEY not in raw:
        return DEMOTE_GRACE_DEFAULT

    candidate = raw[DEMOTE_GRACE_VALUE_KEY]
    # bool is an int subclass, and True would read as one cycle -- the default
    # by accident, which is worse than the default on purpose.
    if isinstance(candidate, bool) or not isinstance(candidate, int):
        logger.warning(
            "%s.%s is %r, not an integer; falling back to the default %d",
            DEMOTE_GRACE_CONFIG_KEY,
            DEMOTE_GRACE_VALUE_KEY,
            candidate,
            DEMOTE_GRACE_DEFAULT,
        )
        return DEMOTE_GRACE_DEFAULT
    if candidate < 0:
        logger.warning(
            "%s.%s=%d is negative; raising to 0, which is the no-hysteresis "
            "end of this knob rather than a demotion that never fires",
            DEMOTE_GRACE_CONFIG_KEY,
            DEMOTE_GRACE_VALUE_KEY,
            candidate,
        )
        return 0
    if candidate > DEMOTE_GRACE_MAX:
        logger.warning(
            "%s.%s=%d exceeds the ceiling %d; clamping. A grace this long "
            "holds a `corroborated` rung on evidence that stopped supporting "
            "it, and the `under-sourced` label bounds that harm without "
            "ending it",
            DEMOTE_GRACE_CONFIG_KEY,
            DEMOTE_GRACE_VALUE_KEY,
            candidate,
            DEMOTE_GRACE_MAX,
        )
        return DEMOTE_GRACE_MAX
    return candidate


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
    # T2.46, and defaulted for the same extensibility reason the field above
    # is. It means exactly "this decision is a demotion the grace window is
    # holding", never "this fact is short of origins": a fact already at
    # `candidate` is short of origins and is not under-sourced, because there
    # is no rung left for the hysteresis to protect. `decide` never sets it —
    # the marker is durable state the applier reads, and `decide` has no
    # session and no clock.
    demotion_pending: bool = False
    # T2.109, defaulted for the same extensibility reason the two fields above
    # are. It means exactly "the Tier-C model scan's standing verdict names a
    # live contradiction against this fact", never "this fact is disputed": it
    # opens review and moves nothing. It is deliberately NOT journalled — the
    # scan already wrote its own `contradiction_scanned` row carrying the
    # counterpart and the judge's reason, so a second copy on the `verified`
    # stream would be redundant state in an append-only journal whose premise
    # is "one row means one transition", and G-C's promotion metrics validate
    # that payload against a closed key vocabulary.
    contradiction_suspected: bool = False


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
    contradiction_suspected: bool = False,
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

    ``contradiction_suspected`` is the Tier-C model scan's finding (T2.109, doc
    08 §4.2's 2026-08-08 amendment). **It is inert here by construction**: no
    branch reads it, it appears in no condition, and every outcome this function
    can return is identical with it set and unset. It exists only to ride the
    returned record, where the contradiction-suspected review opener is what
    acts on it. A judge of the measured precision may flag a fact for a human;
    it may not move a rung, and the way to keep that true is for the signal
    never to reach a branch. Its one interaction with the rest of the ladder is
    the suppression below: doc 08 §4.4 makes a ratified fact immune, and an
    immune fact must not be queued for an adjudication nothing can act on.
    """
    k = profile.origin_count
    n = profile.required_origin_count_for(
        n_diverse=config.n_diverse,
        n_default=config.n_default,
        time_gap_days=config.time_gap_days,
    )
    gate = profile.gate_fired_for(time_gap_days=config.time_gap_days)
    confidence = compute_confidence(origin_count=k, required_n=n, gate_fired=gate)
    suspected = contradiction_suspected and current_status != "confirmed"

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
            contradiction_suspected=suspected,
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

    # Below N. Demotion is immediate *here*, and stays that way: doc 08 §4.3's
    # hysteresis reads durable per-fact state and a clock, neither of which
    # this function may have, so it is interposed at the applier on this
    # first-class `demote` outcome (`apply_demotion_hysteresis`, below).
    if current_status == "corroborated":
        # The count's one exception (doc 08 §4.1, doc 10 §6): a fact a
        # repository's parsed imports assert is born `corroborated` because
        # the parse *is* the verification, and one such origin never reaches
        # N. Without this branch every one of those facts would be demoted by
        # the first recompute that saw it, so the birth would be a label with
        # a lifetime of one tick.
        #
        # **It holds a rung; it never grants one.** Reached only when the
        # fact already sits at `corroborated`, only after the confirmed hold
        # and the absolute veto, and it returns the ordinary unblocked hold —
        # which journals nothing, so no `verified` row is written and G-C's
        # promotion rate sees neither a numerator nor a denominator entry it
        # did not see before. A fact below the rung still climbs by count
        # alone: a candidate a repo also asserts gains a second origin of a
        # second kind, which is the ordinary diversity gate, not this.
        if profile.parse_is_the_verification:
            return settled("corroborated", "hold")
        return settled("candidate", "demote")
    return settled("candidate", "hold")


# ──────────────────────── the demotion hysteresis ────────────────────────


@dataclass(frozen=True)
class HysteresisOutcome:
    """What the grace window did to a decision, and what to persist.

    ``marker`` is ``None`` when the hysteresis columns must be left untouched
    — which is not the same as ``DemotionPending(since=None, cycles=0)``, the
    value that *clears* them. Collapsing the two would make every ordinary
    recompute of an ordinary fact write two columns it has no opinion about.
    """

    decision: LadderDecision
    marker: DemotionPending | None


def apply_demotion_hysteresis(
    decision: LadderDecision,
    *,
    pending_since: datetime | None,
    pending_cycles: int,
    grace_cycles: int,
    now: datetime,
) -> HysteresisOutcome:
    """Doc 08 §4.3: a fact that loses a source does not drop rung immediately.

    **Pure — no I/O, no session, no clock of its own.** ``now`` is supplied by
    the applier, for the same reason ``decide`` reads no clock: replaying the
    same inputs must produce the same answer as the calendar moves. It is
    stamped, never compared, so the answer does not depend on it at all; it
    is the *record* of when the window opened, which is what a human reading
    an under-sourced row wants to know.

    The window is counted in **consecutive recompute cycles**, not in wall
    time, and "consecutive" is enforced by the marker rather than by the
    count: every outcome that is not a demotion clears it, so any cycle
    counted here is one that immediately followed another. That is also why a
    re-corroboration cancels cleanly — cancellation is the same clear, not a
    separate path that could forget a residue.

    **The under-sourced state is a label on a still-``corroborated`` row.**
    The held decision's ``target_status`` is the fact's own current status, so
    no status is written and no ``verified`` row is journalled: the rung did
    not move, and a journal row that claimed it did would be counted by G-C's
    promotion-rate SQL as a transition that never happened. The interim state
    is durable on the row instead (``demotion_pending_since``), served on the
    surfaces this module's own docstring enumerates, and on the review queue.

    ``grace_cycles == 0`` disables the hysteresis outright: the demotion
    applies on the cycle that detects it, no marker is ever written, and the
    label never appears. That is the conservative end of the knob, so it is
    the one value that needs no protection.

    **Confidence is not held back.** The decision's ``confidence`` was
    computed from the *current* origin count, so an under-sourced fact's
    support estimate drops on the cycle the source is lost even though its
    rung does not. That is the intended asymmetry: the badge's claim is
    "asserted by K distinct origins", and K really did fall.
    """
    demoting = decision.outcome == "demote"

    if not demoting:
        # Every non-demotion cancels, including a dispute and a recovery. A
        # fact the veto moved to `disputed` has already lost the rung the
        # window was protecting, so carrying the marker across would resume a
        # count for a demotion from a status the fact no longer holds.
        if pending_since is None:
            return HysteresisOutcome(decision, None)
        return HysteresisOutcome(decision, DemotionPending(since=None, cycles=0))

    if grace_cycles <= 0:
        # No window to open. The marker is cleared rather than left alone so
        # that turning the knob off drains whatever it had already opened,
        # instead of stranding rows wearing a label nothing will ever clear.
        if pending_since is None:
            return HysteresisOutcome(decision, None)
        return HysteresisOutcome(decision, DemotionPending(since=None, cycles=0))

    if pending_since is None:
        held = replace(
            decision,
            target_status=decision.current_status,
            outcome="hold",
            demotion_pending=True,
        )
        return HysteresisOutcome(held, DemotionPending(since=now, cycles=1))

    observed = pending_cycles + 1
    if observed > grace_cycles:
        # The window closed while the fact was still under N. The demotion
        # goes through as `decide` ruled it, and the marker clears with it:
        # the fact is a plain `candidate` now, honestly, with no overlay
        # promising a demotion that has already happened.
        return HysteresisOutcome(decision, DemotionPending(since=None, cycles=0))

    held = replace(
        decision,
        target_status=decision.current_status,
        outcome="hold",
        demotion_pending=True,
    )
    # `since` is deliberately not re-stamped: it records when the window
    # opened, and moving it every cycle would make an under-sourced row look
    # freshly under-sourced however long it had been held.
    return HysteresisOutcome(held, DemotionPending(since=pending_since, cycles=observed))


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


def _under_sourced_opens_review(decision: LadderDecision) -> bool:
    """Doc 08 §6's second fact-side opener: a fact held in demotion hysteresis.

    Keyed off the decision's ``demotion_pending`` flag rather than off the
    ``demotion_pending_since`` column, because the decision is what this cycle
    is about to make true — reading the column would queue on the *previous*
    cycle's state, so the cycle that cancels a demotion would leave the fact
    queued for one more round, and the cycle that opens one would not queue it
    at all.

    The flag is false on the cycle the grace window finally closes, and that
    is correct: the fact demotes to a plain ``candidate``, which is a rung, not
    a condition needing a human. Nothing was silently resolved — the demotion
    it was queued about is exactly what happened, and that transition journals.
    """
    return decision.demotion_pending


def _suspected_contradiction_opens_review(decision: LadderDecision) -> bool:
    """Doc 08 §6's fourth fact-side opener, ratified 2026-08-08 (T2.109).

    The Tier-C model scan found a live contradiction against this fact and the
    ladder is *not* acting on it: the fact keeps its rung, its badge and its
    place in retrieval, and a human decides. That is the whole of the redesign
    — a judge measured at 0.79–0.90 contradiction-precision may surface a
    suspicion, and only the deterministic arm may spend an unappealable veto.

    Keyed off the decision's own flag for the reason
    ``_under_sourced_opens_review`` is: the decision is what this cycle just
    adjudicated, and the verdict was re-validated against today's rows on this
    pass. Reading the journal here instead would queue on a verdict whose
    counterpart may since have expired.

    This opener can fire together with either of the other two, and unlike
    theirs the co-occurrence is reachable rather than theoretical: a fact the
    deterministic arm disputes may also carry a standing model verdict, and an
    under-sourced fact is not excluded from the scan's working set. That is
    exactly the several-openers-one-bit case ``derive_review_state`` exists to
    make safe, and it is why this is a predicate here rather than a writer
    anywhere.
    """
    return decision.contradiction_suspected


# Every condition that puts a fact on the review queue. Registering is what
# makes an opener's condition both able to open the queue and *required* to
# keep it open — ``derive_review_state`` clears only on the absence of every
# member, so a condition plumbed past this tuple would be a queue entry the
# next recompute silently drops. The same binding ``CONTRADICTION_DETECTORS``
# has on the deterministic veto.
#
# The first two members cannot both fire on one decision today: the veto is
# checked before every count, so a contradicted fact leaves ``decide`` on a
# ``dispute`` or a disputed hold, which is not a ``demote`` and therefore
# cancels the hysteresis. That is a property of today's branch order, not of
# the derivation, and the derivation is written to survive its loss — which is
# the whole reason it derives rather than assigns. The third member has no such
# exclusivity with either: T2.109's signal is orthogonal to both, and its
# arrival is what turned that survival property from precaution into use.
REVIEW_OPENERS: tuple[ReviewOpener, ...] = (
    _dispute_opens_review,
    _under_sourced_opens_review,
    _suspected_contradiction_opens_review,
)


def derive_review_state(decision: LadderDecision) -> str | None:
    """Whether this fact belongs on the review queue — derived, never assigned.

    **The ruling (T2.62, 2026-07-31): ``review_state`` is a value recomputed
    from the fact's current conditions at this one point, not a flag each
    opener sets and clears in whatever order it happens to run.** Doc 08 §6
    gives the column four independent openers — a disputed fact (§4.2, this
    one), an under-sourced fact held in hysteresis (§4.3, T2.46), a fact the
    Tier-C model scan suspects a contradiction against (§4.2's 2026-08-08
    amendment, T2.109), and an ungrounded article (doc 09, a *different table*
    and so not a member of ``REVIEW_OPENERS``) — plus a human clearer. The
    fourth arrived after this ruling was written and needed no change to it,
    which is the ruling working: it was appended as a predicate, with no writer
    and no schema. On disk the column is a bare nullable
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

    **What T2.46 did, and it is what this ruling asked for.** The hysteresis
    state is a field on ``LadderDecision`` (``demotion_pending``) — the shape
    T2.06's ruling prescribes for T2.60's ``supersession_blocked`` — with
    ``_under_sourced_opens_review`` registered over it above. T2.46 writes no
    ``review_state`` of its own, and it did not put the ``under-sourced``
    label in this column: the queue predicate and the partial index are both
    the literal ``'open'``, so a row labelled ``'under-sourced'`` is a row
    that has silently left the queue, which is the very failure this ruling
    exists to forbid. The label lives where doc 08 §4.3 put it,
    ``demotion_pending_since``, whose ``IS NOT NULL`` is simultaneously what
    the UI renders and what this tuple's second member is derived from. So the
    companion column this ruling would otherwise have needed already had an
    owner, and T2.62 needed no schema change of its own.

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


# ───────────────── the contradiction's counterpart, on the payload ─────────────────

# The one payload key this adds. A nested block rather than six sibling keys:
# the fields are one finding, and the closed top-level vocabulary that
# ``benchlib.promotion_metrics`` validates every payload against then widens by
# one entry instead of six.
CONTRADICTION_EVIDENCE_KEY = "contradiction"

# What the block's ``enumeration`` field claims, carried as a value rather than
# left to a docstring nobody downstream reads. The adjudication short-circuits
# at the first detector that finds anything, so this is the counterpart the
# verdict turned on, never the complete set of contradictions standing against
# the fact. A consumer may render "disputed by fact X asserting Y"; it may not
# render "the only contradiction", and with the policy on the row it does not
# have to guess which of the two it holds.
ENUMERATION_FIRST_FINDING = "first_finding"


def contradiction_evidence(finding: ContradictionFinding) -> dict[str, str | None]:
    """The finding, reduced to what a human adjudicating actually needs.

    Doc 08 §6 requires disputed knowledge be served labelled with both sides,
    and §4.2's veto is the only thing that ever knows the other side. It is
    discarded once the verdict is taken, so the journal is where it has to be
    recorded: the review queue (T2.22) and the composed result (T2.43) both
    read the latest ``verified`` payload, and neither may re-derive this,
    because the deterministic scan's sole legitimate caller is this module.

    **The copy is deliberately minimal, and the reason is retention.** Journal
    payloads outlive deletion of their subject and the retention policy is an
    open Tier-3 question, so this carries the counterpart's structured triple —
    the competing claim — and not its ``fact`` text, its sources or its
    confidence. The triple is what makes the block readable without a fetch (an
    id alone would satisfy "names the counterpart" while failing "readable from
    the journal alone"); the id is what makes it actionable once the human
    wants the whole row.
    """
    return {
        "counterpart_id": finding.counterpart_id,
        "counterpart_subject": finding.counterpart_subject,
        "counterpart_rel_type": finding.counterpart_rel_type,
        "counterpart_object": finding.counterpart_object,
        "rule": finding.rule,
        "witness_origin": finding.witness_origin,
        "enumeration": ENUMERATION_FIRST_FINDING,
    }


# ─────────────────────────── the applier ───────────────────────────



def _suspicion_marker(finding, *, opened_at, now):
    """The suspicion columns' value for this cycle, or ``None`` to clear them.

    **``since`` is when the flag opened, not when it was last seen.** A finding
    that keeps firing keeps its original timestamp, because the number a
    reviewer needs is how long this has been waiting on them — the same reading
    ``demotion_pending_since`` carries for the sibling opener. Refreshing it
    every cycle would make an old, ignored flag look new on every recompute.

    Returns ``None`` rather than ``UNSET_SUSPICION`` when there is no finding:
    clearing is a real write the ladder owes on every cycle whose guards have
    lapsed, and it is what makes the flag self-clearing on the three grounds
    the 2026-08-08 amendment's cost argument rests on.
    """
    if finding is None:
        return None
    return ContradictionSuspicion(
        since=opened_at or now,
        counterpart_id=finding.counterpart_id,
    )


async def recompute_fact(
    session: AsyncSession,
    fact_id: UUID | str,
    *,
    open_contradiction: ContradictionVerdict = NO_DETECTOR,
    supersession_blocked: bool | None = None,
    contradiction_suspected: bool | None = None,
    now: datetime | None = None,
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

    T2.109's contradiction-suspected flag is adjudicated on the same terms and
    with the same ``None``-means-scan override. It reads the model scan's
    standing verdict through ``detect_scanned_contradiction``, which is
    deliberately called *directly* rather than through the veto's registry:
    that registry is the conjunction that decides whether a dispute may end, so
    a signal that must never end one has no business in it. This is the only
    call site of that function under ``backend/app``, which is what keeps the
    two arms' consumers from being confusable.

    **This is the sole journaller of verification transitions**, which is the
    hand-off ``set_verification_status`` was written anticipating: the only
    write path here is that repository method, so exactly one ``verified``
    event exists per transition and G-C cannot double-count one.

    **The counterpart rides that same payload** (doc 08 §6, "labelled with both
    sides"), and this is the only place it can: the finding is in scope here
    and nowhere else, and it is discarded the moment the verdict is taken. It
    rides *every* payload the scan produced a finding for, which is the dispute
    transition **and** each blocked hold that re-confirms it — not the dispute
    alone. The queue reads the *latest* ``verified`` row per fact, so a
    counterpart carried only on the opening transition would vanish from every
    long-lived dispute on its first re-confirmation, which is exactly the
    population the queue is made of.

    Two shapes carry no counterpart, both honestly. A caller that **overrides**
    the verdict ran no detector here, so nothing was found to name; and a
    ``recover`` was adjudicated clean, so naming the fact it is no longer
    contradicted by would assert a live dispute that no longer stands — in an
    append-only journal, permanently. The opening dispute's own row keeps that
    history.

    T2.46's demotion hysteresis is applied here too, and for the third time
    for the same reason: the grace window's bookkeeping is two columns on the
    row this function already holds under ``FOR UPDATE``, read in the same
    statement as the status so the count cannot be taken against a row the
    applier no longer holds. ``now`` stamps the marker and is a seam for a
    replay or a test; nothing compares it, so supplying it changes what the
    row records and never what the ladder decides.

    A ``fact_id`` with no row returns a hold that writes nothing. The drain
    that will call this races deletion by construction, so raising would turn
    an ordinary race into a failed job.
    """
    config = await get_ladder_config(session)
    grace_cycles = await get_demote_grace_cycles(session)
    profile = await FactSourceRepository(session).origin_profile(fact_id)

    # FOR UPDATE, and it is load-bearing rather than defensive. Without it the
    # row is unlocked between this read and the applier's write, so a
    # concurrently committed `disputed` verdict (T2.04's veto shape) gets
    # overwritten: the decision was taken on a `candidate` the row no longer
    # holds, and the applier journals `disputed -> corroborated` — the
    # contradiction-resolved transition doc 08 §4 reserves for T2.04, emitted by
    # a machine with no detector. Locking from read through write is what makes
    # the decision-layer disputed-hold survive concurrency: the recompute job
    # calls this while human verdicts and ratification write the same row.
    row = await session.execute(
        text(
            "SELECT verification_status, demotion_pending_since, "
            "demotion_pending_cycles, contradiction_suspected_at "
            "FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid) FOR UPDATE"
        ),
        {"id": str(fact_id)},
    )
    locked = row.mappings().first()
    current = locked["verification_status"] if locked is not None else None
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

    finding: ContradictionFinding | None = None
    verdict = open_contradiction
    if verdict is NO_DETECTOR:
        finding = await adjudicate_contradiction_finding(session, fact_id)
        verdict = finding is not None

    blocked = supersession_blocked
    if blocked is None:
        blocked = await adjudicate_supersession_hold(session, fact_id)

    # The finding, not merely whether there is one: doc 08 §6 labels both
    # sides, so the counterpart has to survive as far as the marker write.
    suspicion_finding = None
    suspected = contradiction_suspected
    if suspected is None:
        suspicion_finding = await detect_scanned_contradiction(session, fact_id)
        suspected = suspicion_finding is not None

    decision = decide(
        str(fact_id),
        current,
        profile,
        config,
        open_contradiction=verdict,
        supersession_blocked=blocked,
        contradiction_suspected=suspected,
    )

    hysteresis = apply_demotion_hysteresis(
        decision,
        pending_since=locked["demotion_pending_since"],
        pending_cycles=locked["demotion_pending_cycles"],
        grace_cycles=grace_cycles,
        now=now or datetime.now(timezone.utc),
    )
    decision = hysteresis.decision

    repo = KnowledgeTripleRepository(session)
    # A held fact writes confidence alone: `confirmed` cannot be passed its own
    # status back (the repository refuses it before any read), and a status
    # write that changes nothing would only risk a phantom journal row. The
    # repository still journals on `contradiction_blocked` alone (a reconfirmed
    # `disputed -> disputed` hold) whenever its evidence differs from the
    # latest row, so the evidence rides every call regardless of whether this
    # particular decision carries a status change.
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
        contradiction=contradiction_evidence(finding) if finding is not None else None,
        # UNSET when the caller overrode the signal: a replay re-deciding
        # recorded inputs has no live finding, so it is not the authority on
        # this marker and must not clear one a real scan raised.
        suspicion=(
            UNSET_SUSPICION
            if contradiction_suspected is not None
            else _suspicion_marker(
                # `decide` suppresses the suspicion on a ratified fact, so its
                # marker columns stay clear with it.
                suspicion_finding if current != "confirmed" else None,
                opened_at=locked["contradiction_suspected_at"],
                now=now or datetime.now(timezone.utc),
            )
        ),
        demotion_pending=(
            hysteresis.marker if hysteresis.marker is not None else UNSET_DEMOTION_PENDING
        ),
    )
    return decision

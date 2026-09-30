"""The verification ladder's threshold knobs: resolution, floors, and clamps.

Split out of ``verification_ladder`` by the Flags-tab wiring, and the split is
load-bearing rather than tidiness. Invariant 15 makes the ladder Tier-C only,
and ``tests/test_verification_ladder.py`` enforces it with a tree-wide scan
that matches any line naming that module -- prose included, which is why this
docstring talks around the recompute entry point rather than spelling it. A
settings route reading and writing these thresholds is neither capture nor
retrieval, so exempting it would have meant an allowlist entry -- and an
allowlist entry buys the route the whole module, recompute included. Living
here instead, the config door provably cannot reach it: this module imports no
decision function, and the scan still guards it because it is not on the
allowlist either.

The three thresholds are **floors, not settings** (doc 08 §4.1). A ``config``
row may tighten them freely; loosening one below its shipped default is
honoured only when the ``ladder_measurements`` row names that parameter, from a
recorded G-C measurement. An unbacked loosening is clamped back with a warning
rather than raising -- a bad row degrades to the conservative bar instead of
taking the recompute down, and the conservative bar's failure is a delayed
promotion, which the design accepts.

**Resolution returns a report, and the effective config is derived from it**
(the ``BarReport`` discipline T2.128 established for G-C's promotion bars). A
clamp that speaks only through ``logging`` renders identically to no clamp at
all on every surface an operator actually looks at, so an operator who types 1
into the settings form sees 1 come back and never learns the ladder is still
running at 3. ``resolve_ladder`` carries the committed value, the effective
value and which of *default* / *honoured* / *clamped* happened, per parameter,
and ``get_ladder_config`` folds that same report down to the numbers the
decision needs -- so the reported numbers and the enforced numbers cannot be
two resolutions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories.fact_sources import (
    CORROBORATION_N_DEFAULT,
    CORROBORATION_N_DIVERSE,
    CORROBORATION_TIME_GAP_DAYS,
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

# What happened to one parameter on the way from the config row to the
# decision. `default` means nothing was committed; `honoured` means the
# committed value survived; `clamped` means it did not, and the report says so
# in words rather than leaving the difference for a reader to spot.
LadderParamState = Literal["default", "honoured", "clamped"]


@dataclass(frozen=True)
class LadderParamReport:
    name: str
    committed: int | None
    effective: int
    floor: int
    measured: bool
    state: LadderParamState
    # Present only when `state == "clamped"`: the operator-facing reason, the
    # same sentence the log line carries.
    note: str | None = None


@dataclass(frozen=True)
class LadderReport:
    params: tuple[LadderParamReport, ...]
    # Which parameters the `ladder_measurements` row names. Served so a
    # settings surface can say *why* a below-floor value was honoured, and so
    # "no measurement exists" reads differently from "this one is licensed".
    measured: tuple[str, ...]
    row_present: bool

    def config(self) -> LadderConfig:
        return LadderConfig(**{p.name: p.effective for p in self.params})

    def param(self, name: str) -> LadderParamReport:
        for p in self.params:
            if p.name == name:
                return p
        raise KeyError(name)


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


async def resolve_ladder(session: AsyncSession) -> LadderReport:
    """Resolve the thresholds and report what happened to each one.

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

    reports: dict[str, LadderParamReport] = {}
    for name, floor in LADDER_FLOORS.items():
        is_measured = name in measured
        if name not in raw:
            reports[name] = LadderParamReport(
                name=name,
                committed=None,
                effective=floor,
                floor=floor,
                measured=is_measured,
                state="default",
            )
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
            reports[name] = LadderParamReport(
                name=name,
                committed=None,
                effective=floor,
                floor=floor,
                measured=is_measured,
                state="clamped",
                note=(
                    f"the config row holds {candidate!r}, which is not an "
                    f"integer; running at the shipped default {floor}."
                ),
            )
            continue
        # The floor clamp runs FIRST, and the ordering matters. An earlier
        # revision put the absolute >= 1 bound ahead of this branch and
        # `continue`d past it, so an unmeasured `n_default: 0` never reached
        # its floor: it became 1, then the ordering clamp lifted it to 2, and
        # a two-same-kind-same-day-origin fact promoted where the floor holds
        # at 3 — an operator typo manufacturing exactly the counterfeit
        # corroboration D3 exists to prevent. Every floor is >= 1, so clamping
        # here already satisfies the absolute bound for the unmeasured case.
        if candidate < floor and not is_measured:
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
            reports[name] = LadderParamReport(
                name=name,
                committed=candidate,
                effective=floor,
                floor=floor,
                measured=False,
                state="clamped",
                note=(
                    f"{candidate} is below the minimum of {floor}, so {floor} "
                    "is used. Going lower needs a recorded measurement."
                ),
            )
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
            reports[name] = LadderParamReport(
                name=name,
                committed=candidate,
                effective=1,
                floor=floor,
                measured=is_measured,
                state="clamped",
                note=(
                    f"{candidate} is below the absolute minimum of 1, so 1 is "
                    "used. A fact always needs at least one source."
                ),
            )
            continue
        reports[name] = LadderParamReport(
            name=name,
            committed=candidate,
            effective=candidate,
            floor=floor,
            measured=is_measured,
            state="honoured",
        )

    # The ordering invariant is NOT unlockable by measurement. n_default is the
    # ungated bar and n_diverse the gated one, so n_default < n_diverse inverts
    # the ladder: firing a gate would *raise* N, and corroborating evidence
    # would make promotion harder. No measurement can make that coherent, so
    # unlike the three floors this clamps unconditionally.
    if reports["n_default"].effective < reports["n_diverse"].effective:
        n_diverse = reports["n_diverse"].effective
        prior = reports["n_default"]
        logger.warning(
            "%s has n_default=%d below n_diverse=%d, which inverts the ladder; "
            "raising n_default to %d. This clamp is not unlockable by measurement.",
            LADDER_CONFIG_KEY,
            prior.effective,
            n_diverse,
            n_diverse,
        )
        reports["n_default"] = LadderParamReport(
            name="n_default",
            committed=prior.committed,
            effective=n_diverse,
            floor=prior.floor,
            measured=prior.measured,
            state="clamped",
            note=(
                f"n_default ({prior.effective}) cannot be lower than "
                f"n_diverse ({n_diverse}), so {n_diverse} is used."
            ),
        )

    return LadderReport(
        params=tuple(reports[name] for name in LADDER_FLOORS),
        measured=tuple(sorted(measured)),
        row_present=row is not None,
    )


async def get_ladder_config(session: AsyncSession) -> LadderConfig:
    """The effective thresholds: merge over defaults, validate, clamp.

    Derived from ``resolve_ladder`` rather than resolving a second time, so the
    numbers a settings surface prints and the numbers the decision enforces are
    the same resolution by construction.
    """
    report = await resolve_ladder(session)
    return report.config()

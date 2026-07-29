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

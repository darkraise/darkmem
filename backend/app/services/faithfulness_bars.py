"""TH1.01 — the faithfulness metric's bars, committed before any of Lane A exists.

Span-support coverage (doc 16 par.4: entailed answer-claims / total
answer-claims) is defined, barred and committed **before** the system it
measures is built — doc 20 par.4's ordering rule, the same discipline that
committed ``promotion_bars.py`` before G-C's first measurement and
``coverage_bars.py`` before G-E's. The full definition, the derivations and
the claim/span gold shape live in
``docs/superpowers/specs/2026-08-15-faithfulness-metric-and-bar-design.md``;
this module is the goalposts, and ``tests/test_faithfulness_bars.py`` pins
every default by value so moving one is a visible two-file diff, never a
quiet constant tweak.

The three bars
--------------

- **``faithfulness_coverage_bar`` = 1.0** — the per-answer serving boundary:
  an answer is served *as grounded* only when every sentence is entailed by
  its cited block spans. Derived, not chosen: doc 16's own below-bar label is
  "could not *fully* ground this answer", so the grounded label asserts full
  grounding; the label is binary, so its guarantee must be length-invariant;
  and for answers under 20 sentences every bar in (18/19, 1.0] is the same
  predicate anyway — the article twin's 0.95 diverges only where it leaks
  (39/40 = 0.975 serves an unsupported sentence under the grounded badge).
  The anti-fit check: 1.0 is the one value no laundering argument reaches —
  every fit loosens, and there is nothing above 1.0 to loosen from. The
  fitted value would be the twin's 0.95, and the pin test pins against
  exactly that.
- **``faithfulness_gate_precision_bar`` = 0.95** and
  **``faithfulness_gate_recall_bar`` = 0.90** — the faithfulness *role*'s
  judge qualification bars on claim/span gold, by doc 17 par.6's standing
  rule (truth-critical metric 0.95, the other 0.90; the rule predates every
  judge run). Precision on ``entailed`` is truth-critical: a judge that calls
  an unsupported sentence entailed serves a hallucination under the grounded
  badge. Same numbers as the groundedness pair because the rule and the
  discrimination are the same; the record, the gold and the sitting are not
  shared.

All three are the owner's to move with a recorded argument; none may be moved
to make a run pass.

Floors, per-parameter direction, and the licence
------------------------------------------------

Every bar here is a **floor** — verified against its comparison site
(coverage >= bar, precision >= bar, recall >= bar) and re-derived from the
predicates by test rather than asserted, because G-C's clamp found a bar
whose abuse a direction-blind guard read as a tightening. The direction is
carried per parameter (``FaithfulnessBarSpec.conservative``) so a future bar
cannot join this module direction-unstated.

Tightening is free. A readable ``config`` row below its floor is honoured
only against a ``faithfulness_bar_licences`` row naming that parameter,
stating the lowest value its recorded argument supports, and citing where
the argument lives — the T2.126/T2.127 shape, reused rather than a fourth
mechanism. Otherwise it clamps back to the committed default (never to the
licensed value, which would put a number on the gate the operator did not
write) with a warning naming what was missing. An unreadable bar row raises,
and enforcement fails closed on it. Nothing in this tree writes the licence
row. Note ``faithfulness_coverage_bar`` sits at the top of its domain, so a
config row can only restate or loosen it: every genuine move on that key
takes a licence.

Consumers, stated before they exist
-----------------------------------

TH1.09's serving check reads ``get_faithfulness_bars`` and decides with
``answer_grounded``; TH1.17's gate runner and the ``faithfulness`` judge
role's wiring (``JUDGE_ROLES`` / ``BAR_METRICS``) **import** these defaults
and never restate them, so the bars stated today and the bars enforced then
cannot be two values. Until the role lands, the two gate bars live only
here, on purpose: a bar orphaned into no role's gate is exactly what the
roles-partition test forbids.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class Conservative(Enum):
    """Which way a bar has to move to make its gate harder to clear."""

    HIGHER = "higher"


@dataclass(frozen=True)
class FaithfulnessBarSpec:
    """One bar's committed number and the direction that number defends."""

    default: float
    conservative: Conservative

    def loosens(self, candidate: float) -> bool:
        return candidate < self.default


FAITHFULNESS_BARS: dict[str, FaithfulnessBarSpec] = {
    "faithfulness_coverage_bar": FaithfulnessBarSpec(1.0, Conservative.HIGHER),
    "faithfulness_gate_precision_bar": FaithfulnessBarSpec(
        0.95, Conservative.HIGHER
    ),
    "faithfulness_gate_recall_bar": FaithfulnessBarSpec(
        0.90, Conservative.HIGHER
    ),
}

# Derived, so adding a bar cannot leave its direction unstated.
FAITHFULNESS_BAR_DEFAULTS: dict[str, float] = {
    key: spec.default for key, spec in FAITHFULNESS_BARS.items()
}

FAITHFULNESS_BAR_LICENCES_KEY = "faithfulness_bar_licences"

_BARS_SQL = text("""
    SELECT key, value FROM config WHERE key = ANY(CAST(:keys AS text[]))
""")


def parse_faithfulness_bar_licences(row_value: object) -> dict[str, float]:
    """Which bars carry a licence to sit below their floor, and how far down.

    Shape, mirroring ``verification_bar_licences`` exactly::

        {"licensed": {"<bar key>": {"value": 0.95,
                                    "argument": "gate-ledger.md#<section>"}}}

    Permission is per parameter and per value: an entry unlocks its own
    parameter down to its own stated value and nothing else. A malformed
    entry licenses nothing and says which field is missing, because the
    operator whose value was ignored is the one who has to read that line.
    """
    if row_value is None:
        return {}

    licensed = row_value.get("licensed") if isinstance(row_value, dict) else None
    if not isinstance(licensed, dict):
        logger.warning(
            "%s config row is %r, not {\"licensed\": {<bar key>: {\"value\": x, "
            "\"argument\": \"<where the argument is recorded>\"}}}; licensing "
            "nothing, so every bar holds at its floor",
            FAITHFULNESS_BAR_LICENCES_KEY,
            row_value,
        )
        return {}

    out: dict[str, float] = {}
    for key, entry in licensed.items():
        if key not in FAITHFULNESS_BARS:
            logger.warning(
                "%s licenses %r, which is not a faithfulness bar; ignoring. "
                "Licensable parameters: %s",
                FAITHFULNESS_BAR_LICENCES_KEY,
                key,
                sorted(FAITHFULNESS_BARS),
            )
            continue
        if not isinstance(entry, dict):
            logger.warning(
                "%s licence for %s is %r, not an object carrying value and "
                "argument; licensing nothing for it",
                FAITHFULNESS_BAR_LICENCES_KEY,
                key,
                entry,
            )
            continue
        value = entry.get("value")
        # bool is an int subclass, and False would read as a licence down to 0.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            logger.warning(
                "%s licence for %s states value %r, not a number; licensing "
                "nothing for it. A licence must say how far down the recorded "
                "argument reaches, or it bounds nothing",
                FAITHFULNESS_BAR_LICENCES_KEY,
                key,
                value,
            )
            continue
        bound = float(value)
        # A bound at or below zero can never be tripped, so it would unlock
        # the parameter outright and silently — a bound that bounds nothing.
        if not math.isfinite(bound) or not 0.0 < bound <= 1.0:
            logger.warning(
                "%s licence for %s states value %r, which is not a bar value "
                "in (0, 1]; licensing nothing for it. A licence at or below "
                "zero would unlock the parameter outright and no candidate "
                "could ever trip its own bound",
                FAITHFULNESS_BAR_LICENCES_KEY,
                key,
                value,
            )
            continue
        argument = entry.get("argument")
        if not isinstance(argument, str) or not argument.strip():
            logger.warning(
                "%s licence for %s states no argument citation; licensing "
                "nothing for it. The citation is what a reviewer checks the "
                "loosening against — its presence is all this code can verify, "
                "and its absence is all it takes to refuse",
                FAITHFULNESS_BAR_LICENCES_KEY,
                key,
            )
            continue
        out[key] = bound
    return out


def _clamp_to_floor(
    key: str, candidate: float, licensed: dict[str, float]
) -> float:
    spec = FAITHFULNESS_BARS[key]
    if not spec.loosens(candidate):
        return candidate

    allowed = licensed.get(key)
    if allowed is None:
        logger.warning(
            "%s=%s is below its floor %s and the %s row licenses no loosening "
            "for it; clamping to %s. Lowering a faithfulness bar takes a "
            "licence naming this parameter, the lowest value its recorded "
            "argument supports, and where that argument is recorded — never "
            "an edit to the bar row alone.",
            key,
            candidate,
            spec.default,
            FAITHFULNESS_BAR_LICENCES_KEY,
            spec.default,
        )
        return spec.default
    if candidate < allowed:
        # Back to the floor rather than to `allowed`: clamping to the licensed
        # value would adopt a number the operator did not write, on an
        # argument they did not make for it.
        logger.warning(
            "%s=%s is below its floor %s and below the %s licence's own "
            "lowest licensed value %s; clamping to %s. The licence bounds how "
            "far the bar may move, so going further takes a new licence and a "
            "new recorded argument.",
            key,
            candidate,
            spec.default,
            FAITHFULNESS_BAR_LICENCES_KEY,
            allowed,
            spec.default,
        )
        return spec.default
    return candidate


def resolve_faithfulness_bars(rows: dict[str, object]) -> dict[str, float]:
    """Merge raw ``config`` values over the committed defaults, DB winning per
    key, then clamp any unlicensed loosening back to its floor.

    A row's value may be ``{"value": x}`` or a bare JSON number. An unreadable
    row raises rather than reverting to the default — silently ignoring an
    operator's attempt to move a bar is conservative relative to the default
    but not to operator intent (the ``get_verification_bars`` posture,
    inherited verbatim). A readable row below its floor is a statement this
    code can act on, so it degrades to the floor with a warning instead of
    taking the serving path down.

    ``rows`` carries the raw ``config`` values, including
    ``faithfulness_bar_licences`` when the database holds one.
    """
    licensed = parse_faithfulness_bar_licences(
        rows.get(FAITHFULNESS_BAR_LICENCES_KEY)
    )

    bars = dict(FAITHFULNESS_BAR_DEFAULTS)
    for key in FAITHFULNESS_BARS:
        if key not in rows:
            continue
        value = rows[key]
        if isinstance(value, dict):
            value = value.get("value")
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            raise ValueError(
                f"config row {key} carries an unreadable bar value "
                f"{rows[key]!r}; fix or delete the row"
            )
        bars[key] = _clamp_to_floor(key, float(value), licensed)
    return bars


async def get_faithfulness_bars(session: AsyncSession) -> dict[str, float]:
    result = await session.execute(
        _BARS_SQL,
        {"keys": [*FAITHFULNESS_BAR_DEFAULTS, FAITHFULNESS_BAR_LICENCES_KEY]},
    )
    return resolve_faithfulness_bars({row.key: row.value for row in result})


# ── the pre-stated verdict predicates ────────────────────────────────────


def answer_grounded(
    entailed_claims: int, total_claims: int, bars: dict[str, float]
) -> bool:
    """May this answer be served *as grounded*?

    Takes counts, not a rate: 39/40 and 975/1000 are the same 0.975 and not
    the same evidence, and a rate cannot express the zero-claim refusal. An
    answer with no claims grounds nothing — coverage 0/0 is refused, never
    vacuously cleared, so an empty or all-label body cannot collect the
    strongest label the surface serves.
    """
    if total_claims < 0 or entailed_claims < 0 or entailed_claims > total_claims:
        raise ValueError(
            f"incoherent claim counts: entailed={entailed_claims} "
            f"total={total_claims}"
        )
    if total_claims == 0:
        return False
    return entailed_claims / total_claims >= bars["faithfulness_coverage_bar"]


def faithfulness_role_clears(
    entailed_precision: float, entailed_recall: float, bars: dict[str, float]
) -> bool:
    """Does a claim/span qualification run clear the faithfulness role's bars?"""
    return (
        entailed_precision >= bars["faithfulness_gate_precision_bar"]
        and entailed_recall >= bars["faithfulness_gate_recall_bar"]
    )

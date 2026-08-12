"""T2.40 — the G-C bars, stated and committed before any measurement runs.

``promotion_metrics`` produces numbers and refuses judgment by design
(runbook §2: the model that wrote the harness must not decide whether its
number is good enough). This module is the judgment's fixed goalposts: the
bar for each of G-C's four probes, committed **ahead of the first
measurement commit** so the git history itself witnesses the ordering
gate-ledger.md rule 1 demands. A bar written after seeing the number is not
a bar; a default edited to fit a result is the same thing one file over,
which is why ``tests/test_promotion_bars.py`` pins every default by value —
moving a goalpost must show up as a deliberate two-file diff, never a quiet
constant tweak.

**Shape follows G-D's precedent** (``verification_judge.py``'s
``VERIFICATION_BAR_DEFAULTS`` / ``get_verification_bars``): each bar is a
named ``config``-row key merged over a committed code default, DB winning
per key, an unreadable row raising rather than silently reverting to the
default. The rows are read from the **measured** database's ``config``
table; on a database that carries none, the committed defaults below are
the bars, exactly as G-D's ledger rows record theirs as "config default".
Since T2.127 the precedent's *clamp* follows too, in this module's own
direction per bar — see "Why these bars are clamped" below.

The four probes and their bars
------------------------------

1. **Promotion rate, by source-kind diversity** and 2. **by which N fired**
   (``_PROMOTION_RATE_BY_DIVERSITY_SQL`` / ``_PROMOTION_RATE_BY_GATE_SQL``):

   - *Decidability*: an axis is decidable only when at least one of its
     buckets is powered — ``eligible >= promotion_rate_min_eligible`` (the
     harness's own ``UNDER_POWERED_THRESHOLD``, imported so the two cannot
     drift) — **and** the window carries at least
     ``promotion_rate_min_promotions`` journaled ``promote`` outcomes.
     The second clause is the Done-when's "facts have actually flowed
     through the ladder": a window in which nothing ever promoted cannot
     evidence a promotion ladder, whatever its rate arithmetic says.
   - *Bar*: every **powered** bucket must clear
     ``promotion_rate_floor`` (promoted / eligible ≥ 0.5). Eligible rows
     all met their origin bar; the non-promoted remainder are veto
     disputes and supersession-blocked holds. On a healthy corpus those
     are the exception. A powered bucket where they are the majority means
     either corpus-wide contradiction or a misfiring veto — and the veto's
     instrument is the very judge whose interim contradiction-precision
     measured **0.818 against a 0.95 bar** (T2.26) — so the gate holds
     there pending diagnosis rather than clearing over it. 0.5 is stated
     judgement, deliberately loose: this floor exists to catch a ladder
     that mostly refuses its own eligible facts, not to tune the rate.
   - Under-powered buckets are reported with their denominators (rule 4:
     never collapsed) and can neither clear nor fail the floor.

3. **False-promotion audit** (``_FALSE_PROMOTED_FACTS_SQL``):

   - *Bar*: rate **< 0.01**, strict, under the key doc 17 §5.1 itself
     names (``verification_false_promotion_bar``, recommended start 1%).
     The rate is the harness's implemented quantity: DISTINCT corroborated
     facts later disputed or human-rejected, over DISTINCT facts
     corroborated in the window.
   - *Decidability*: ``false_promotion_min_corroborations`` (20). Below
     100 corroborations a single false promotion already breaches 1%, so
     within the decidable band this bar effectively demands **zero**
     observed false promotions — the same small-set granularity G-D's
     interim recorded ("one false accept ≈ 0.944", i.e. the bar is
     "zero errors" until the set grows). 20 is where a zero stops being
     an artifact of an empty window and starts being an observation.

4. **Every ladder transition journaled** — bar **100 %**
   (``promotion_journal_completeness_bar`` = 1.0), measured as the
   reconciliation in ``JOURNAL_COMPLETENESS_SQL`` below: zero fact rows
   whose ``verification_status`` the ``verified`` journal cannot explain.

Definitional rulings recorded WITH the bars
-------------------------------------------

These decide what the audit counts, so they are committed before any
count exists.

**R1 — a citation-driven downgrade is not a false promotion (T2.48).**
The citation re-verifier marks a code citation stale and the recompute
*demotes* the citing fact — deliberately never ``disputed``, because a
deleted symbol may be a rename a human should confirm. The audit's
numerator stays "later disputed or human-rejected" and excludes these
demotions, for three reasons. First, the audit measures promotion
*precision* — was the fact wrong when the ladder promoted it — and a
stale citation is evidence *withdrawal* under world change, not a finding
of falsity; the system's own refusal to write ``disputed`` says so.
Second, counting demotions would couple the false-promotion rate to
repository churn: every refactor of an indexed repo would raise the one
number that vetoes threshold loosening, for reasons unrelated to
promotion correctness. Third, nothing is lost in the unsafe direction:
the demoted fact loses its badge immediately, and if the claim is later
found actually false, the dispute or rejection enters the numerator
through the normal doors. One boundary case is accepted and stated: a
fact promoted on a citation that was **already stale at promotion time**
(staleness is detected one ``citation_reverify`` tick after reindex)
appears only as a demote and is invisible to the audit; the exposure is
bounded by one reverify cron period, after which the stale row stops
counting toward any future promotion (``LIVE_SOURCE_PREDICATE``).

**R2 — the fold identity blind spot (T2.101), direction stated.** An
entity-merge fact fold keeps the higher-rung row's id and journals no
``verified`` row — correct, no promotion escapes the ladder. But the
audit joins corroboration and dispute on ``object_id``, and a fold can
put those on different ids: if the keeper's ``corroborated`` rung was
never journaled (a born-corroborated row) while the retired row's
promotion was, a later dispute lands on the keeper's id, where no
corroboration event exists — the pair never joins and a genuine false
promotion goes uncounted. Direction: the audit **undercounts** —
anti-conservative, the one direction this metric must not err in
silently. Scope: requires a fold whose keeper holds an unjournaled rung,
i.e. exactly the born-corroborated interaction. Any measurement run must
therefore report the in-window fold count (``expired`` events on facts
carrying a prior in-window corroboration) beside the audit, and a
non-zero count caps what the audit's zero can claim.

**R3 — the born-rung carve-out in the completeness probe, enumerated.**
``_write_born_rung`` writes ``corroborated`` without journaling on two
paths sharing one statement: the deriver birth (no transition occurred —
nothing to journal) and the post-dispute **restore**
(``restore_born_corroborated``), which IS a ``candidate → corroborated``
status change that journals nothing, on doc 10 §6's argument that the
rung rests on the parse, not on a promotion decision. The completeness
probe carves out exactly the rows that licence covers — facts at
``corroborated`` whose provenance is exclusively ``source_kind='code'``
— and **counts the carve-out** rather than absorbing it: the number is
reported beside the probe so the claim stays "100 % of counting-ladder
transitions journaled, N born-rung rows excluded by the stated licence",
never a bare 100 %.

Why these bars are clamped, and what the clamp is worth here
-----------------------------------------------------------

T2.127, owner-ruled 2026-08-13, recorded in doc 17 §6 beside the judge's
own clamp. **The argument is not T2.126's and is deliberately not
borrowed from it.** A lowered ``groundedness_gate_precision_bar`` admits
a judge that calls ungrounded claims grounded, and the cost lands on a
person reading a badge. Nothing in this module decides a badge. These six
decide whether G-C's verdict is *evaluable* and whether it *cleared* — a
number a human writes up, and the evidence record that lights the
promoted badge (``promotion_metrics_record.json``) is minted only from a
cleared run. So the failure this clamp prevents is narrower and slower: a
``config`` row written between runs turns "under-powered, gate stays
open" into "cleared", and the report prints the moved number as though it
had always been the bar. **Nobody writes down why, because there is
nothing to write down** — no source diff, no review, no ledger entry, and
the pin test one file over reads these constants and holds no session.

It is worth taking anyway, for a reason specific to this gate rather than
inherited: **G-C has come back under-powered on every probe it has run**
(T2.111, 2026-08-08 — no fact has ever exited ``candidate`` in any journal
this machine can see), and the pressure on these six numbers grows as the
corpus fills and the cutover waits behind the gate. The most exposed are
the *decidability* thresholds, where lowering
``false_promotion_min_corroborations`` or ``promotion_rate_min_eligible``
does not make a failing gate pass — it makes an under-powered window
speak, which is the same move one step earlier and reads cleaner in a
report than a lowered pass mark does.

**The conservative direction is a per-bar property, and five of these six
point the opposite way from the judge's four.** G-D's bars are uniformly
higher-is-stricter, so a floor plus a clamp upward is that module's whole
story. Here, verified against the comparison site of each bar rather than
assumed (``tests/test_promotion_bars.py`` re-derives every row of this
table from the predicates, so a mis-stated direction fails the build):

===================================== ========= ================== =========================
bar                                   compared  conservative       loosening it does
===================================== ========= ================== =========================
verification_false_promotion_bar      ``rate <``  **lower**        tolerates a higher
                                                  (a ceiling)      false-promotion rate
false_promotion_min_corroborations    ``>=``      higher           lets a thinner window
                                                  (a floor)        become decidable
promotion_rate_floor                  ``>=``      higher           passes a bucket that
                                                                   refuses more of its own
promotion_rate_min_eligible           ``>=``      higher           powers a thinner bucket
promotion_rate_min_promotions         ``<``       higher           lets a window with no
                                                                   promotions be decidable
promotion_journal_completeness_bar    (unread)    higher           nothing today — see below
===================================== ========= ================== =========================

A guard that only refused *downward* moves would dutifully protect five
of these and leave the single most abusable one wide open: raising
``verification_false_promotion_bar`` from 0.01 to 0.05 tolerates five
times the false-promotion rate and would pass such a guard as a
"tightening".

**Two things this clamp does not do, stated rather than discovered.**

*One:* ``promotion_journal_completeness_bar`` is read by **nothing**.
``journal_completeness_clears`` takes no ``bars`` at all — the 100 % bar
is spelled as its only satisfiable form, zero unexplained rows — so a
``config`` row moving that bar changes no verdict today. Its direction is
stated and its clamp holds for a future consumer; it is prophylactic, and
calling it a live protection would overstate what is here.

*Two:* tightening is free, and for ``promotion_rate_min_eligible`` free
is not the same as harmless. That default is imported from the harness's
``UNDER_POWERED_THRESHOLD`` precisely so the report's "powered" and this
module's "decidable" cannot become two claims; a ``config`` row raising
it is conservative for the verdict and still splits those two numbers.
That belongs in a source diff, where the import can move with it, not in
a row this clamp waves through.

**The honest limit is the same as T2.126's.** An operator with
config-write access can write the bar row and the licence row together,
and nothing in-process stops that. What the clamp buys is that a
loosening is no longer a single number edit that leaves no trace.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from benchlib.promotion_metrics import UNDER_POWERED_THRESHOLD

logger = logging.getLogger(__name__)


class Conservative(Enum):
    """Which way a bar has to move to make the gate harder to clear."""

    HIGHER = "higher"
    LOWER = "lower"


@dataclass(frozen=True)
class BarSpec:
    """One bar's committed number and the direction that number defends.

    ``licence_limit`` is the edge of the bar's own domain **in its
    loosening direction** — the value a licence bound may not reach,
    because a bound there or beyond can never be tripped by any candidate
    and so unlocks the parameter silently. It is stated per bar rather
    than assumed because the six do not share one: the five floors (three
    counts, two rates) run out at 0, and the one rate ceiling at 1.
    """

    default: float | int
    conservative: Conservative
    licence_limit: float

    def loosens(self, candidate: float) -> bool:
        if self.conservative is Conservative.HIGHER:
            return candidate < self.default
        return candidate > self.default

    def beyond(self, candidate: float, bound: float) -> bool:
        if self.conservative is Conservative.HIGHER:
            return candidate < bound
        return candidate > bound

    def bound_is_coherent(self, bound: float) -> bool:
        if not math.isfinite(bound):
            return False
        if self.conservative is Conservative.HIGHER:
            return bound > self.licence_limit
        return bound < self.licence_limit


# The direction and the limit are stated beside the value they belong to,
# never in a parallel table: a bar whose conservative direction nobody
# stated cannot be merged safely, and two mappings keyed alike is the
# drift shape this arrangement exists to avoid.
PROMOTION_BARS: dict[str, BarSpec] = {
    # doc 17 §5.1's own key and recommended starting value. Strict `<`, and
    # the one CEILING here: raising it tolerates a higher false-promotion
    # rate. A rate cannot exceed 1, so a licence at 1.0 bounds nothing.
    "verification_false_promotion_bar": BarSpec(
        0.01, Conservative.LOWER, licence_limit=1.0
    ),
    "false_promotion_min_corroborations": BarSpec(
        20, Conservative.HIGHER, licence_limit=0.0
    ),
    "promotion_rate_floor": BarSpec(0.5, Conservative.HIGHER, licence_limit=0.0),
    # Imported, never re-typed: the harness's reporting floor and the gate's
    # per-bucket power floor must be one number or the ledger's "powered"
    # and this module's "decidable" drift into two claims.
    "promotion_rate_min_eligible": BarSpec(
        UNDER_POWERED_THRESHOLD, Conservative.HIGHER, licence_limit=0.0
    ),
    "promotion_rate_min_promotions": BarSpec(
        1, Conservative.HIGHER, licence_limit=0.0
    ),
    "promotion_journal_completeness_bar": BarSpec(
        1.0, Conservative.HIGHER, licence_limit=0.0
    ),
}

# Derived, so adding a bar cannot leave its direction unstated. The name and
# the shape are the pinned public ones (`tests/test_promotion_bars.py`).
PROMOTION_BAR_DEFAULTS: dict[str, float | int] = {
    key: spec.default for key, spec in PROMOTION_BARS.items()
}

# T2.127: the shape is T2.126's, per parameter and bounded, not a third
# mechanism. What the row asserts is only what code can check — which
# parameter (by name, never blanket), how far the recorded argument reaches
# (so the licence *bounds* the loosening rather than blessing whatever the
# bar row says), and where that argument lives (a citation checked for
# presence and never for truth). Nothing in this tree writes it.
PROMOTION_BAR_LICENCES_KEY = "promotion_bar_licences"

_BARS_SQL = text("""
    SELECT key, value FROM config WHERE key = ANY(CAST(:keys AS text[]))
""")


def parse_promotion_bar_licences(row_value: object) -> dict[str, float]:
    """Which bars carry a licence to sit past their conservative bound.

    Shape, mirroring ``get_verification_bar_licences``::

        {"licensed": {"<bar key>": {"value": 0.4,
                                    "argument": "gate-ledger.md#<section>"}}}

    ``value`` is the furthest the recorded argument reaches **in that
    bar's own loosening direction** — the lowest value for a floor, the
    highest for the false-promotion ceiling. A malformed entry licenses
    nothing and says which field is missing, because the operator whose
    value was ignored is the one who has to read that line.
    """
    if row_value is None:
        return {}

    licensed = row_value.get("licensed") if isinstance(row_value, dict) else None
    if not isinstance(licensed, dict):
        logger.warning(
            "%s config row is %r, not {\"licensed\": {<bar key>: {\"value\": x, "
            "\"argument\": \"<where the argument is recorded>\"}}}; licensing "
            "nothing, so every bar holds at its committed value",
            PROMOTION_BAR_LICENCES_KEY,
            row_value,
        )
        return {}

    out: dict[str, float] = {}
    for key, entry in licensed.items():
        spec = PROMOTION_BARS.get(key)
        if spec is None:
            logger.warning(
                "%s licenses %r, which is not a G-C bar; ignoring. Licensable "
                "parameters: %s",
                PROMOTION_BAR_LICENCES_KEY,
                key,
                sorted(PROMOTION_BARS),
            )
            continue
        if not isinstance(entry, dict):
            logger.warning(
                "%s licence for %s is %r, not an object carrying value and "
                "argument; licensing nothing for it",
                PROMOTION_BAR_LICENCES_KEY,
                key,
                entry,
            )
            continue
        value = entry.get("value")
        # bool is an int subclass, and False would read as a licence to 0.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            logger.warning(
                "%s licence for %s states value %r, not a number; licensing "
                "nothing for it. A licence must say how far the recorded "
                "argument reaches, or it bounds nothing",
                PROMOTION_BAR_LICENCES_KEY,
                key,
                value,
            )
            continue
        bound = float(value)
        if not spec.bound_is_coherent(bound):
            logger.warning(
                "%s licence for %s states value %r, which is at or past the "
                "%s edge of that bar's domain (%s); licensing nothing for it. "
                "No candidate could ever fall past such a bound, so it would "
                "unlock the parameter outright and silently",
                PROMOTION_BAR_LICENCES_KEY,
                key,
                value,
                spec.conservative.value,
                spec.licence_limit,
            )
            continue
        argument = entry.get("argument")
        if not isinstance(argument, str) or not argument.strip():
            logger.warning(
                "%s licence for %s states no argument citation; licensing "
                "nothing for it. The citation is what a reviewer checks the "
                "loosening against — its presence is all this code can verify, "
                "and its absence is all it takes to refuse",
                PROMOTION_BAR_LICENCES_KEY,
                key,
            )
            continue
        out[key] = bound
    return out


def _clamp_to_conservative(
    key: str, candidate: float, licensed: dict[str, float]
) -> float:
    spec = PROMOTION_BARS[key]
    if not spec.loosens(candidate):
        return candidate

    allowed = licensed.get(key)
    if allowed is None:
        logger.warning(
            "%s=%s moves the bar %s than its committed %s, which loosens G-C, "
            "and the %s row licenses no loosening for it; clamping to %s. "
            "Moving a G-C bar away from its conservative direction takes a "
            "licence naming this parameter, the furthest value its recorded "
            "argument supports, and where that argument is recorded — never an "
            "edit to the bar row alone.",
            key,
            candidate,
            "lower" if spec.conservative is Conservative.HIGHER else "higher",
            spec.default,
            PROMOTION_BAR_LICENCES_KEY,
            spec.default,
        )
        return float(spec.default)
    if spec.beyond(candidate, allowed):
        # Back to the committed bar rather than to `allowed`: clamping to the
        # licensed value would put a number on the gate that the operator
        # never wrote, on an argument they did not make for it.
        logger.warning(
            "%s=%s loosens past the %s licence's own bound %s; clamping to %s. "
            "The licence bounds how far the bar may move, so going further "
            "takes a new licence and a new recorded argument.",
            key,
            candidate,
            PROMOTION_BAR_LICENCES_KEY,
            allowed,
            spec.default,
        )
        return float(spec.default)
    return candidate


def resolve_promotion_bars(rows: dict[str, object]) -> dict[str, float]:
    """Merge raw ``config`` values over the committed defaults, DB winning
    per key, then clamp any unlicensed loosening back to the committed bar.

    An unreadable row raises rather than reverting to the default —
    silently ignoring an operator's attempt to move a bar is conservative
    relative to the default but not to operator intent (the
    ``get_verification_bars`` posture, inherited verbatim). A readable row
    that merely points the wrong way is a statement this code can act on,
    so it degrades to the committed bar with a warning instead of taking
    the run down (T2.127; the same split G-D's reader draws).

    ``rows`` carries the raw ``config`` values, including
    ``promotion_bar_licences`` when the measured database holds one.
    """
    licensed = parse_promotion_bar_licences(rows.get(PROMOTION_BAR_LICENCES_KEY))

    bars = {key: float(value) for key, value in PROMOTION_BAR_DEFAULTS.items()}
    for key, value in rows.items():
        if key not in PROMOTION_BAR_DEFAULTS:
            continue
        if isinstance(value, dict):
            value = value.get("value")
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        ):
            bars[key] = _clamp_to_conservative(key, float(value), licensed)
        else:
            raise ValueError(
                f"config row {key} carries an unreadable bar value {value!r}; "
                f"fix or delete the row"
            )
    return bars


async def get_promotion_bars(session: AsyncSession) -> dict[str, float]:
    result = await session.execute(
        _BARS_SQL,
        {"keys": [*PROMOTION_BAR_DEFAULTS, PROMOTION_BAR_LICENCES_KEY]},
    )
    return resolve_promotion_bars({row.key: row.value for row in result})


# ── the pre-stated verdict predicates ────────────────────────────────────


def audit_decidable(total_corroborations: int, bars: dict[str, float]) -> bool:
    return total_corroborations >= bars["false_promotion_min_corroborations"]


def audit_clears(
    rate: float | None, total_corroborations: int, bars: dict[str, float]
) -> bool:
    if rate is None or not audit_decidable(total_corroborations, bars):
        return False
    return rate < bars["verification_false_promotion_bar"]


def slice_powered(eligible: int, bars: dict[str, float]) -> bool:
    return eligible >= bars["promotion_rate_min_eligible"]


def slice_clears(promoted: int, eligible: int, bars: dict[str, float]) -> bool:
    """A powered bucket clears the floor; an unpowered one never clears."""
    if not slice_powered(eligible, bars):
        return False
    return promoted / eligible >= bars["promotion_rate_floor"]


def axis_decidable(
    slices: list[tuple[int, int]], total_promotions: int, bars: dict[str, float]
) -> bool:
    """``slices`` is ``[(promoted, eligible), ...]`` for one axis."""
    if total_promotions < bars["promotion_rate_min_promotions"]:
        return False
    return any(slice_powered(eligible, bars) for _, eligible in slices)


def journal_completeness_clears(violations: int) -> bool:
    """Bar 1.0 spelled as its only satisfiable form: zero unexplained rows."""
    return violations == 0


# ── probe 4's measurement, stated before any run ─────────────────────────

# Reconciliation of `knowledge_triples.verification_status` against the
# `verified` journal. A row is EXPLAINED when its column equals the latest
# journaled `after.verification_status` — or, for a row with no `verified`
# events, equals the lift's birth status `candidate` — or falls under R3's
# born-rung carve-out (status `corroborated`, journal absent or tailing
# `candidate`, provenance exclusively `source_kind='code'`). Everything
# else is a violation: a status the journal cannot account for, which is
# precisely the unmeasurable transition the 100 % bar forbids. Unwindowed
# on purpose — completeness is a property of the corpus, not of a window.
JOURNAL_COMPLETENESS_SQL = """
WITH journal_final AS (
    SELECT DISTINCT ON (object_id)
           object_id,
           payload->'after'->>'verification_status' AS journal_status
    FROM events
    WHERE event_type = 'verified' AND object_type = 'fact'
    ORDER BY object_id, created_at DESC, id DESC
),
code_only AS (
    SELECT fact_id
    FROM fact_sources
    GROUP BY fact_id
    HAVING COUNT(*) FILTER (WHERE source_kind <> 'code') = 0
)
SELECT
    COUNT(*) AS facts,
    COUNT(*) FILTER (
        WHERE kt.verification_status = 'corroborated'
          AND COALESCE(jf.journal_status, 'candidate') = 'candidate'
          AND co.fact_id IS NOT NULL
    ) AS born_rung_carveout,
    COUNT(*) FILTER (
        WHERE kt.verification_status
              IS DISTINCT FROM COALESCE(jf.journal_status, 'candidate')
          AND NOT (
              kt.verification_status = 'corroborated'
              AND COALESCE(jf.journal_status, 'candidate') = 'candidate'
              AND co.fact_id IS NOT NULL
          )
    ) AS violations
FROM knowledge_triples kt
LEFT JOIN journal_final jf ON jf.object_id = kt.id
LEFT JOIN code_only co ON co.fact_id = kt.id
"""

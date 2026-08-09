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
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from benchlib.promotion_metrics import UNDER_POWERED_THRESHOLD

PROMOTION_BAR_DEFAULTS: dict[str, float | int] = {
    # doc 17 §5.1's own key and recommended starting value. Strict `<`.
    "verification_false_promotion_bar": 0.01,
    "false_promotion_min_corroborations": 20,
    "promotion_rate_floor": 0.5,
    # Imported, never re-typed: the harness's reporting floor and the gate's
    # per-bucket power floor must be one number or the ledger's "powered"
    # and this module's "decidable" drift into two claims.
    "promotion_rate_min_eligible": UNDER_POWERED_THRESHOLD,
    "promotion_rate_min_promotions": 1,
    "promotion_journal_completeness_bar": 1.0,
}


_BARS_SQL = text("""
    SELECT key, value FROM config WHERE key = ANY(CAST(:keys AS text[]))
""")


def resolve_promotion_bars(rows: dict[str, object]) -> dict[str, float]:
    """Merge raw ``config`` values over the committed defaults, DB winning.

    An unreadable row raises rather than reverting to the default —
    silently ignoring an operator's attempt to move a bar is conservative
    relative to the default but not to operator intent (the
    ``get_verification_bars`` posture, inherited verbatim).
    """
    bars = {key: float(value) for key, value in PROMOTION_BAR_DEFAULTS.items()}
    for key, value in rows.items():
        if key not in PROMOTION_BAR_DEFAULTS:
            continue
        if isinstance(value, dict):
            value = value.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            bars[key] = float(value)
        else:
            raise ValueError(
                f"config row {key} carries an unreadable bar value {value!r}; "
                f"fix or delete the row"
            )
    return bars


async def get_promotion_bars(session: AsyncSession) -> dict[str, float]:
    result = await session.execute(
        _BARS_SQL, {"keys": list(PROMOTION_BAR_DEFAULTS)}
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

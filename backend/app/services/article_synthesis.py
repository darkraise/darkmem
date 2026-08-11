"""Article synthesis — the productive runs (T3.02, doc 09 §4.2).

An eligible subject in (T3.01), one stored article out, synthesised from
verified facts only and journalled so a bad article is traceable to its fact
set.

**The exclusion is a ``WHERE``, and that is a safety property rather than a
performance note.** Doc 09 §4.2 names two load-bearing exclusions — disputed
facts and candidate facts — and the done-when says "excluded at the query, not
filtered from the draft". The difference matters because a filter applied to a
*draft* removes facts and leaves prose: the model has already seen the disputed
fact and may have written a sentence whose citation no longer supports it, and
that sentence survives the filter. So a fact that must not ground an article is
never loaded.

**One statuses constant, not two.** ``VERIFIED_STATUSES`` is
:mod:`app.services.article_eligibility`'s, imported rather than restated: the
subject that *earned* an article and the facts that *fill* it must agree on
what "verified" counts as, and two copies is how they stop agreeing. The
eligibility module's own docstring makes the same point about resolving the set
in one place.

**What is deliberately not excluded.** A ``corroborated`` fact carrying
``contradiction_suspected_at`` is still a synthesis input. Doc 09 §4.2 names
two exclusions and no suspicion flag, and T2.109 moved the LLM contradiction
scan off every suppressive path after measuring it at 0.79–0.90 against a 0.95
bar — a flagged fact "keeps its rung, its badge and its place in retrieval".
Excluding it here would hand a sub-bar instrument a new suppressive channel, in
which a false positive silently drops a *true* corroborated fact from its
article. Adding the exclusion is a Tier-3 amendment to §4.2, not a tightening
anyone may make at a call site.

**Recency's basis is the belief window, then the clock.** §4.2 fixes the
ranking as ``confidence × read-heat × recency`` and does not say what recency
is measured from. A fact's ``reference_time`` is when the claim is *about*,
which is what "recent knowledge" means for a fact; ``created_at`` is when
darkmem heard it. ``reference_time`` is ``NOT NULL`` on the table, so it is the
basis, and the fallback exists only for defence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.article_eligibility import VERIFIED_STATUSES

__all__ = [
    "DEFAULT_HUB_CAP",
    "GatheredFact",
    "gather_facts",
]

# Doc 09 §4.2's hub cap: "top-K facts by fact-salience", K a `config` row
# "defaulting modest, e.g. 40". The cap does three jobs — it keeps a hub like
# `postgres` from producing an unreadable essay, it keeps the article focused,
# and because an article's claim count is bounded by its fact count it bounds
# the cost of T3.03's per-claim entailment pass. K and the length budget are
# two knobs on the same lever.
DEFAULT_HUB_CAP = 40

# Half-life for the recency term, in days. A fact stated a year ago is not
# worthless — it is less salient than one stated last week, which is what a
# decay expresses and a cutoff does not. Exponential rather than linear so the
# term is bounded in (0, 1] and cannot go negative and invert the product.
RECENCY_HALF_LIFE_DAYS = 180.0

# Facts carry a nullable `confidence`. A fact with none is not a fact with no
# confidence in it — it is one nothing measured — so it ranks at the same
# neutral value `memories.confidence` defaults to rather than at zero, which
# would drop every unmeasured fact below every measured one regardless of heat.
NEUTRAL_CONFIDENCE = 0.75


@dataclass(frozen=True)
class GatheredFact:
    """One verified fact, as a synthesis input.

    Carries the fields §4.2's grouping needs (``rel_type``, ``applies_when``)
    and the fields the draft needs (``fact``, the endpoint names), plus the
    ranking inputs so a caller can explain an ordering without re-querying.
    """

    id: str
    subject_name: str
    rel_type: str
    object_name: str
    fact: str
    applies_when: dict[str, Any] | None
    learned_in: list[str]
    confidence: float
    read_heat: float
    reference_time: datetime | None
    salience: float


# Doc 09 §4.2's predicate, verbatim: the subject's non-disputed
# corroborated/confirmed facts, unexpired. `disputed` and `candidate` are both
# `verification_status` values, so the `= ANY` clause is what implements both
# named exclusions — the flowchart's separate `AND not disputed` restates the
# first rather than adding a third.
#
# Ranked in SQL rather than in Python because the cap is a `LIMIT`: pulling a
# hub's several hundred facts across the wire to drop all but forty would make
# the cap a readability knob only, and §4.2 makes it a cost knob too.
_FACTS_SQL = text(
    """
    SELECT t.id,
           t.subject_name,
           t.rel_type,
           t.object_name,
           t.fact,
           t.applies_when,
           t.learned_in,
           t.confidence,
           t.reference_time,
           COALESCE(a.access_count, 0) AS read_heat,
           (
               COALESCE(t.confidence, CAST(:neutral AS double precision))
               * (1 + COALESCE(a.access_count, 0))
               * exp(
                   -GREATEST(
                       EXTRACT(EPOCH FROM (CAST(:now AS timestamptz) - t.reference_time))
                       / 86400.0,
                       0
                   ) * ln(2) / CAST(:half_life AS double precision)
               )
           ) AS salience
    FROM knowledge_triples t
    LEFT JOIN fact_access_stats a ON a.fact_id = t.id
    WHERE t.project = CAST(:project AS text)
      AND lower(t.subject_name) = CAST(:subject AS text)
      AND t.verification_status = ANY(CAST(:statuses AS text[]))
      AND t.expired_at IS NULL
    ORDER BY salience DESC, t.id
    LIMIT :cap
    """
)


async def gather_facts(
    session: AsyncSession,
    *,
    subject: str,
    project: str = "default",
    cap: int = DEFAULT_HUB_CAP,
    now: datetime | None = None,
) -> list[GatheredFact]:
    """The subject's verified facts, ranked by §4.2's salience and capped.

    ``subject`` is matched lower-cased, matching how ``article_eligibility``
    groups subjects (``lower(t.subject_name)``): entity names are stored
    lower-cased and the eligibility scan keys on that, so a caller handing back
    the ``name_lower`` it was given finds the same rows.

    ``now`` is a parameter rather than a clock read so the ranking is testable
    for equality — the same reason ``inject_block.render_block`` takes its
    ``generated_at``.

    **Read-heat is computed here, never read from a stored column.** Doc 09
    §4.1 is explicit that heat is "computed at job time, never a stored heat
    column that would go stale"; the substrate is ``fact_access_stats``, the
    fact-keyed counter, joined exactly as the eligibility scan joins it.
    """
    stamp = now or datetime.now(timezone.utc)
    rows = (
        await session.execute(
            _FACTS_SQL,
            {
                "project": project,
                "subject": subject.lower(),
                "statuses": list(VERIFIED_STATUSES),
                "cap": max(0, cap),
                "now": stamp,
                "neutral": NEUTRAL_CONFIDENCE,
                "half_life": RECENCY_HALF_LIFE_DAYS,
            },
        )
    ).mappings().all()

    return [
        GatheredFact(
            id=str(row["id"]),
            subject_name=row["subject_name"],
            rel_type=row["rel_type"],
            object_name=row["object_name"],
            fact=row["fact"],
            applies_when=row["applies_when"],
            learned_in=list(row["learned_in"] or []),
            confidence=(
                float(row["confidence"])
                if row["confidence"] is not None
                else NEUTRAL_CONFIDENCE
            ),
            read_heat=float(row["read_heat"]),
            reference_time=row["reference_time"],
            salience=float(row["salience"]),
        )
        for row in rows
    ]

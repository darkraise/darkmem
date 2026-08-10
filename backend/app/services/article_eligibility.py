"""Subject eligibility and priority scoring for article synthesis (doc 09
§4.1) — T3.01.

Doc 09's central algorithmic call is that salience is **neither** pure fact
count, nor pure retrieval frequency, nor pure community centrality, but a
*gated composite*: fact count is a hard gate, and the other two only decide
ordering among subjects that already cleared it.

**The gate runs before the score, and that ordering is the design.** "An
article that cannot be grounded is worse than no article", so a subject below
the floor is ineligible regardless of how central or how frequently read it is.
This module makes that structural rather than conventional: an ineligible
candidate carries ``priority=None``, and no code path computes a number for
one. A reader reaching for ``.priority`` therefore cannot be handed a ranking
for a subject doc 09 says must not be ranked.

**Which vocabulary the floor counts, and why it differs from
``pin_suggestions``.** That module counts verified facts in the vocabulary a
reader is *served* — resolved through ``claim_gates.raw_statuses_for_served``
— because it hands a human a nomination carrying a count, and a count the
reader could not have computed from what they were shown is an oracle. With
G-C's record absent, its floor is closed. **This module counts the stored
labels instead**, and the difference is deliberate:

* Nothing here reaches a reader. The output is a work list for T3.02, which is
  itself held shut by G-D — the epic's entry gate — and which is where a
  synthesised article first asserts groundedness to anybody. Gating the work
  list too would gate one claim twice while telling no one anything.
* Doc 09 §4.1 states the gate in doc 08's stored labels ("non-disputed
  corroborated/confirmed"), and the eligibility question it asks is about what
  the vault *holds*, not about what it may currently say out loud.
* A served-vocabulary floor here would be closed today, so this module would
  ship inert and every test of its eligible path would have to mint a
  promotion record to reach it.

The counted set is resolved in **one** place (:data:`VERIFIED_STATUSES`), so a
future owner who decides the serving vocabulary should govern here too changes
one binding rather than auditing the SQL.

**The consequence a reader-facing door would inherit.** ``verified_fact_count``
on the returned candidate is a stored-vocabulary number. Nothing serves it
today — this module has no route and no door — but a surface that rendered it
while G-C's record is absent would be handing a reader exactly the count the
claim gate withholds, which is the oracle ``pin_suggestions`` gates against.
A door over this module therefore owes the same inversion that module does; it
is registered in ``AGGREGATES_NAMING_THE_RUNG`` so that obligation is visible
from the sweep rather than only from here.

**Weights are ``config`` rows here, and are code constants in
``review_ranking``.** That module states its reason plainly — an
operator-editable weight invites the untracked retune the measurement
discipline exists to forbid. Doc 09 §4.1 nonetheless puts each ``w_*`` in a
``config`` row, tuned "from measured synthesis value via doc 17", and the task
carries that as a done-when. Both survive together only under one reading, so
it is written down here: **the config row makes a measured retune deployable
without a release; it does not license an unmeasured one.** Moving a weight on
intuition is the same violation it would be in ``rank_fusion`` — the row is
where the number lives, not permission to pick it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from math import isfinite, log1p

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories.pinned_subjects import get_subject_lists
from app.services.pin_suggestions import subject_soft_key

logger = logging.getLogger(__name__)

__all__ = [
    "ARTICLE_SELECTION_CONFIG_KEY",
    "SubjectCandidate",
    "SynthesisConfig",
    "candidate_subjects",
    "get_synthesis_config",
    "select_for_synthesis",
    "subject_soft_key",
]

# Deliberately NOT `article_synthesis`: that is the dream-job family member's
# own key, and a module naming it is a module invariant 15's source scan reads
# as routing to a Tier-C job — correctly, since it could not tell a config row
# from a trigger. The collision was also a real ambiguity rather than only a
# scan artefact: this row configures *selection*, and the job's own parameters
# live under `job:article_synthesis`.
ARTICLE_SELECTION_CONFIG_KEY = "article_selection"

# Doc 08's rungs, in the stored vocabulary. `disputed` and `candidate` are
# absent for two different reasons and both are load-bearing: a disputed fact
# is not settled understanding, and a candidate fact is not verified at all,
# so counting either would ground an article in something the vault has not
# established. See the module docstring for why this is the stored set rather
# than the served one.
VERIFIED_STATUSES: tuple[str, ...] = ("corroborated", "confirmed")

DEFAULT_MIN_VERIFIED_FACTS = 3
DEFAULT_SYNTHESIS_BUDGET = 5

# Conservative by default, per doc 09 §4.1: fact count leads because it is the
# signal the gate already trusts, and the two ordering-only signals are damped
# below it until a measurement says otherwise.
DEFAULT_W_FACTS = 1.0
DEFAULT_W_HEAT = 0.5
DEFAULT_W_CENTRAL = 0.5

PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "min_verified_facts": (1, 1000),
    "synthesis_budget": (1, 1000),
    "w_facts": (0.0, 100.0),
    "w_heat": (0.0, 100.0),
    "w_central": (0.0, 100.0),
}

_INT_PARAMS = ("min_verified_facts", "synthesis_budget")

_PARAM_DEFAULTS: dict[str, float] = {
    "min_verified_facts": DEFAULT_MIN_VERIFIED_FACTS,
    "synthesis_budget": DEFAULT_SYNTHESIS_BUDGET,
    "w_facts": DEFAULT_W_FACTS,
    "w_heat": DEFAULT_W_HEAT,
    "w_central": DEFAULT_W_CENTRAL,
}


@dataclass(frozen=True)
class SynthesisConfig:
    """The five operator-tunable numbers, already validated and clamped."""

    min_verified_facts: int = DEFAULT_MIN_VERIFIED_FACTS
    synthesis_budget: int = DEFAULT_SYNTHESIS_BUDGET
    w_facts: float = DEFAULT_W_FACTS
    w_heat: float = DEFAULT_W_HEAT
    w_central: float = DEFAULT_W_CENTRAL


DEFAULT_SYNTHESIS_CONFIG = SynthesisConfig()


@dataclass(frozen=True)
class SubjectCandidate:
    """One subject, with the gate's answer and — only then — its ordering.

    ``priority`` is ``None`` exactly when ``eligible`` is False. That is not a
    convenience: doc 09 forbids an ineligible subject being ranked at all, and
    a dataclass that could carry both would let a later caller quietly restore
    score-first behaviour by reading the number anyway.
    """

    subject_key: str
    project: str
    verified_fact_count: int
    read_heat: float
    centrality: int
    pinned: bool
    eligible: bool
    priority: float | None


async def get_synthesis_config(session: AsyncSession) -> SynthesisConfig:
    """The effective parameters: merge over defaults, validate, clamp.

    The row is operator-edited with no schema in front of it, so every
    malformed shape degrades loudly rather than raising — an unknown key is
    ignored with a warning naming it, an unparseable value falls back to its
    default, and an out-of-range value is clamped. A bad row must not take the
    synthesis job down; it must also never silently mean something other than
    what it says, which is why each of the three degradations logs.
    """
    result = await session.execute(
        select(Config).where(Config.key == ARTICLE_SELECTION_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    raw = row.value if row is not None and isinstance(row.value, dict) else {}

    for key in raw:
        if key not in _PARAM_DEFAULTS:
            logger.warning(
                "%s config row carries unknown key %r; ignoring. Known keys: %s",
                ARTICLE_SELECTION_CONFIG_KEY,
                key,
                sorted(_PARAM_DEFAULTS),
            )

    values: dict[str, float] = {}
    for name, default in _PARAM_DEFAULTS.items():
        if name not in raw:
            values[name] = default
            continue
        try:
            parsed = float(raw[name])
        except (TypeError, ValueError):
            logger.warning(
                "%s.%s is %r, which is not a number; falling back to %r",
                ARTICLE_SELECTION_CONFIG_KEY, name, raw[name], default,
            )
            values[name] = default
            continue
        if not isfinite(parsed):
            # `min`/`max` propagate NaN rather than clamping it, so the clamp
            # below "succeeded" and then `int(nan)` raised -- taking the job
            # down, which is the one thing this loader exists not to do. In a
            # weight it was worse: no raise, and every priority silently NaN.
            logger.warning(
                "%s.%s is %r, which is not a finite number; falling back to %r",
                ARTICLE_SELECTION_CONFIG_KEY, name, raw[name], default,
            )
            values[name] = default
            continue
        low, high = PARAM_BOUNDS[name]
        if not low <= parsed <= high:
            clamped = min(max(parsed, low), high)
            logger.warning(
                "%s.%s is %r, outside [%s, %s]; clamping to %r",
                ARTICLE_SELECTION_CONFIG_KEY, name, parsed, low, high, clamped,
            )
            parsed = clamped
        values[name] = parsed

    return SynthesisConfig(
        min_verified_facts=int(values["min_verified_facts"]),
        synthesis_budget=int(values["synthesis_budget"]),
        w_facts=values["w_facts"],
        w_heat=values["w_heat"],
        w_central=values["w_central"],
    )


# The three signals in one statement, keyed by the subject soft key.
#
# `subjects` is built from the facts themselves rather than from `entities`,
# so a subject exists here only if the vault asserts something about it. The
# entity join supplies `entity_type` for the soft key and the id the centrality
# arm needs; a fact whose `subject_id` never resolved falls back to `concept`,
# which is the same fallback `normalize_entity_type` gives an unknown type.
#
# Heat is read through `fact_access_stats` — the fact-keyed counter T2.84
# landed — summed over the subject's own verified facts. It is a *subject*
# signal here, not a fact one, so SUM is right where `review_ranking`'s MAX is:
# that module ranks facts against each other and must not reward a fact for
# having many sources, while this one asks how much of a subject's knowledge
# gets read at all.
_CANDIDATES_SQL = text(
    """
    WITH verified AS (
        SELECT t.id,
               t.subject_id,
               lower(t.subject_name) AS name_lower
        FROM knowledge_triples t
        WHERE t.project = CAST(:project AS text)
          AND t.verification_status = ANY(CAST(:statuses AS text[]))
          AND t.expired_at IS NULL
    ),
    subjects AS (
        -- Grouped on the whole soft key, never the name alone. Uniqueness on
        -- `entities` is `(name, entity_type)`, so one name can be two
        -- subjects; pooling them summed two floors into one a neither had
        -- earned, keyed the result by the lexicographically smallest type,
        -- and left centrality reading whichever id that group happened to
        -- pick. Type-constrained dedup (Phase 4) makes the same distinction
        -- upstream for the same reason.
        SELECT v.name_lower,
               COALESCE(e.entity_type, 'concept') AS entity_type,
               MIN(CAST(v.subject_id AS text)) AS entity_id,
               COUNT(*) AS verified_fact_count,
               COALESCE(SUM(a.access_count), 0) AS read_heat
        FROM verified v
        LEFT JOIN entities e ON e.id = v.subject_id
        LEFT JOIN fact_access_stats a ON a.fact_id = v.id
        GROUP BY v.name_lower, COALESCE(e.entity_type, 'concept')
    )
    SELECT s.name_lower,
           s.entity_type,
           s.verified_fact_count,
           CAST(s.read_heat AS double precision) AS read_heat,
           COALESCE((
               SELECT COUNT(DISTINCT n.neighbour_id)
               FROM (
                   SELECT r.target_entity_id AS neighbour_id
                   FROM entity_relations r
                   WHERE r.source_entity_id = CAST(s.entity_id AS uuid)
                     AND r.target_entity_id <> CAST(s.entity_id AS uuid)
                   UNION ALL
                   SELECT r.source_entity_id AS neighbour_id
                   FROM entity_relations r
                   WHERE r.target_entity_id = CAST(s.entity_id AS uuid)
                     AND r.source_entity_id <> CAST(s.entity_id AS uuid)
               ) n
           ), 0) AS centrality
    FROM subjects s
    """
)

# Subjects a human pinned may hold no facts at all, so they cannot come from
# the statement above — it is built from facts by construction. Their heat and
# centrality still resolve, by name, through the entity the pin names.
_PINNED_SIGNALS_SQL = text(
    """
    SELECT COALESCE((
               SELECT COUNT(DISTINCT n.neighbour_id)
               FROM (
                   SELECT r.target_entity_id AS neighbour_id
                   FROM entity_relations r
                   WHERE r.source_entity_id = e.id AND r.target_entity_id <> e.id
                   UNION ALL
                   SELECT r.source_entity_id AS neighbour_id
                   FROM entity_relations r
                   WHERE r.target_entity_id = e.id AND r.source_entity_id <> e.id
               ) n
           ), 0) AS centrality
    FROM entities e
    WHERE e.name = CAST(:name_lower AS text)
      AND e.entity_type = CAST(:entity_type AS text)
    LIMIT 1
    """
)

_LIVE_ARTICLE_SUBJECTS_SQL = text(
    "SELECT subject_key FROM knowledge_articles "
    "WHERE project = CAST(:project AS text) AND status <> 'superseded'"
)


def _priority(candidate_signals: tuple[int, float, int], config: SynthesisConfig) -> float:
    """``w_facts·facts + w_heat·heat + w_central·centrality``, damped.

    Each signal is passed through ``ln(1+x)`` before weighting, the same
    compression ``review_ranking`` applies for the same reason: these are
    unbounded counts on different scales, and a hub with four hundred
    neighbours must not be able to swamp the weights by arithmetic alone. The
    weights then decide the trade, which is what a weight is for.

    **This is doc 09 §4.1's formula as of 2026-08-10, and it was not when this
    shipped.** §4.1 stated the linear composite; this module damped and its
    docstring presented that as implementing the doc rather than deviating from
    it, which the E3 branch review caught (T3.01 Minor 4). Ruling R-D adopted
    the damping into §4.1 by Tier-3 amendment rather than reverting it here, on
    the reasoning recorded there. The consequence that binds a future reader:
    the curve is part of what a weight-tune is measured *against*, so a retune
    moves ``w_*`` and never the ``ln(1+x)``.
    """
    facts, heat, centrality = candidate_signals
    return (
        config.w_facts * log1p(facts)
        + config.w_heat * log1p(heat)
        + config.w_central * log1p(centrality)
    )


async def candidate_subjects(
    session: AsyncSession, *, project: str, config: SynthesisConfig | None = None
) -> list[SubjectCandidate]:
    """Every known subject for ``project``, gated and — where eligible — scored.

    Returns the ineligible ones too, carrying ``eligible=False`` and no
    priority: a caller diagnosing "why was nothing synthesised" needs to see
    the subjects that were considered and how far short they fell, and
    filtering them out here would make that answerable only by re-running the
    query by hand.
    """
    config = config or await get_synthesis_config(session)
    pinned, _dismissed = await get_subject_lists(session, project)

    rows = (await session.execute(
        _CANDIDATES_SQL, {"project": project, "statuses": list(VERIFIED_STATUSES)}
    )).mappings().all()

    candidates: list[SubjectCandidate] = []
    seen: set[str] = set()
    for row in rows:
        key = subject_soft_key(row["name_lower"], row["entity_type"])
        seen.add(key)
        candidates.append(
            _build(
                key, project, row["verified_fact_count"], float(row["read_heat"]),
                int(row["centrality"]), key in pinned, config,
            )
        )

    # A pinned subject is eligible whatever the vault holds, so it must appear
    # even when it anchors no verified fact — which is exactly when the
    # fact-built statement above cannot produce it.
    for key in sorted(pinned - seen):
        try:
            name_lower, entity_type = key.rsplit("::", 1)
        except ValueError:
            logger.warning(
                "pinned subject key %r is not a soft key; ignoring for synthesis", key
            )
            continue
        centrality = (await session.execute(
            _PINNED_SIGNALS_SQL, {"name_lower": name_lower, "entity_type": entity_type}
        )).scalar_one_or_none()
        candidates.append(
            _build(key, project, 0, 0.0, int(centrality or 0), True, config)
        )

    return candidates


def _build(
    key: str,
    project: str,
    facts: int,
    heat: float,
    centrality: int,
    pinned: bool,
    config: SynthesisConfig,
) -> SubjectCandidate:
    """The gate, then — and only then — the score.

    The early return is the whole of doc 09 §4.1's ordering: an ineligible
    subject leaves here with no priority computed, so there is no number for a
    later caller to rank by.
    """
    eligible = pinned or facts >= config.min_verified_facts
    if not eligible:
        return SubjectCandidate(
            subject_key=key, project=project, verified_fact_count=facts,
            read_heat=heat, centrality=centrality, pinned=pinned,
            eligible=False, priority=None,
        )
    return SubjectCandidate(
        subject_key=key, project=project, verified_fact_count=facts,
        read_heat=heat, centrality=centrality, pinned=pinned,
        eligible=True, priority=_priority((facts, heat, centrality), config),
    )


async def select_for_synthesis(
    session: AsyncSession, *, project: str, config: SynthesisConfig | None = None
) -> list[SubjectCandidate]:
    """The eligible subjects this run should synthesise, in priority order.

    Subjects that already carry a live article are excluded: the budget exists
    for subjects with *no* article, and re-synthesis of an existing one is
    T3.05's staleness gate on its own trigger. Spending the run's budget on
    re-synthesis would starve first articles indefinitely, since a hub's
    priority does not fall once it has been written up.

    The sort is ``(-priority, subject_key)`` — a total order. A tie broken by
    whatever order the planner returned would let one run's budget cut a tied
    list differently from the next, so the same corpus would synthesise
    different subjects on consecutive runs with nothing having changed.
    """
    config = config or await get_synthesis_config(session)
    candidates = await candidate_subjects(session, project=project, config=config)

    existing = {
        row[0] for row in (await session.execute(
            _LIVE_ARTICLE_SUBJECTS_SQL, {"project": project}
        )).all()
    }

    eligible = [
        c for c in candidates
        if c.eligible and c.subject_key not in existing
    ]
    return order_for_budget(eligible, config)


def order_for_budget(
    eligible: list[SubjectCandidate], config: SynthesisConfig
) -> list[SubjectCandidate]:
    """Priority order, cut to the budget — pure, and separated for that reason.

    The tie-break is only observable when two subjects tie, and whether the
    database hands back a tied pair in one order or the other is not something
    a test can pin. Keeping the ordering pure lets the tie be constructed
    directly, so the guard can actually fail when the tie-break is removed —
    a stable sort would otherwise preserve the arrival order and look correct.
    """
    ineligible = [c.subject_key for c in eligible if not c.eligible]
    if ineligible:
        # `-(priority or 0.0)` used to adopt 0.0 here, so handing this the
        # output of `candidate_subjects` -- which deliberately includes
        # ineligibles -- filled spare budget with subjects that cleared no
        # floor. Raising rather than filtering: a caller passing one in has
        # made a mistake, and silently dropping it would hide the mistake at
        # exactly the seam T3.02 consumes.
        raise ValueError(
            "ineligible subjects cannot be ordered: doc 09 §4.1 gates before "
            f"it scores, and these carry no priority to rank by: {ineligible[:5]}"
        )
    ordered = sorted(eligible, key=lambda c: (-(c.priority or 0.0), c.subject_key))
    return ordered[: config.synthesis_budget]

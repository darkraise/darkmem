"""Consequence ranking and dispute-staleness decay for the review queue
(doc 08 §6, T2.24).

Doc 08 §6 asks for a queue "ranked by **consequence** — retrieval frequency
and subject salience — not arrival order, so the fact an agent hits every day
is triaged before a dormant one". Neither input exists as a fact-level number,
so both are derived here. Every derivation below is a proxy, and each one's
failure mode is named rather than implied.

**Retrieval frequency — the recency-decayed peak over a fact's source
memories.** ``memory_access_stats`` (T2.29's counters, keyed ``memory_id``) is
bridged to a fact through its ``('memory', <memory id>)`` ``fact_sources``
rows. The aggregate is ``MAX``, not ``SUM`` and not ``AVG``:

* ``SUM`` rewards a fact for *having many sources*, which is precisely what
  corroboration already rewards — the same evidence would then count twice,
  once as verification support and again as consequence, and a widely-sourced
  but never-read fact would outrank a single-sourced one an agent hits daily.
* ``AVG`` is worse than either: adding a cold source to a fact *lowers* its
  consequence, so accumulating evidence would demote a fact down the queue.
  A ranking that punishes evidence is a ranking nobody can defend.
* ``MAX`` is monotone under new sources (never decreases), invariant to how
  many there are, and answers the question doc 08 actually asks: a fact an
  agent hits every day is a fact with at least one memory the agent hits
  every day.

Recency is folded in *before* the max, not after: each source contributes
``access_count * 0.5 ** (age_of_last_access / access_half_life_days)``, so the
peak picked is the source that is hottest **now**. A fact hit fifty times a
year ago is not the fact an agent hits every day, and without the decay it
would outrank it forever.

*Failure mode.* The counter measures **memory** retrieval, not fact retrieval,
so the attribution is a proxy: a memory may be retrieved for reasons that have
nothing to do with the fact lifted from it, and a fact with several sources
inherits the heat of whichever one happens to be popular. It is also
cold-start biased — a freshly lifted fact has no access history through no
fault of its own and scores zero — and blind to non-memory provenance: a fact
sourced only by ``human`` or ``code`` rows scores zero on this axis forever,
because those refs name no ``memories`` row. Both biases point the same way
(understating a new or human-sourced fact), which is why salience is a
separate arm rather than a tiebreak.

**Subject salience — distinct graph neighbours of the subject entity.** Of the
three candidates (live facts sharing the ``subject_name``, memories whose
``technologies`` array mentions it, entity degree in ``entity_relations``),
only the third is not a raw mention count. ``entity_relations`` is UNIQUE on
``(source_entity_id, target_entity_id, rel_type)`` and re-assertion appends to
``memory_ids`` instead of inserting a row, so degree counts *distinct
relationships the vault knows about*, not how often something was talked
about. Counting distinct **neighbours** rather than distinct edges compresses
it once more: a subject joined to one neighbour by five relation types is
connected to one thing, not five.

*Failure mode, stated plainly.* It is still a popularity measure, just of the
graph rather than of the corpus. A hub entity accrues degree from every
incidental mention, so a trivial fact about a hub subject can outrank a
consequential fact about a niche one; and the graph's shape reflects what the
extractor names often, not what the maintainer cares about. Two things bound
the damage: the count is log-compressed, so a hub with 200 neighbours is worth
about twice a subject with 14 rather than fourteen times as much, and the arm
carries half the weight of retrieval frequency — retrieval frequency is
measured from real agent behaviour, salience is a structural guess, and doc 08
names them in that order. A third case is a *correct* zero rather than a
failure: a subject whose entity the orphan sweep has pruned has left the
graph, and "no graph presence" is what zero salience means.

**The resolution of a fact's subject is ``subject_id``, not ``subject_name``.**
``fact_lift`` writes both, and the pointer is a primary-key lookup while the
name is not usable: ``knowledge_triples.subject_name`` is canonicalised
(lowered, stripped, interior whitespace collapsed) while ``entities.name`` is
only lowered and stripped, so an equality join is subtly wrong for any name
with interior double whitespace and the canonicalising join is unindexable
(``fact_lift._canon`` documents the same trap). A NULL or dangling
``subject_id`` therefore reads as zero salience, which is a degradation in one
direction only — it understates, never overstates.

**The decay changes priority and nothing else.** A dispute that has stood past
``dispute_stale_days`` sorts into a lower tier. It is *not* a status: nothing
here writes ``verification_status`` (the fact stays ``disputed``), nothing
writes ``review_state`` (T2.62's ruling forbids it, and
``derive_review_state``'s docstring says so by name), and the membership
predicate is untouched, so a decayed dispute is still on the queue, still
counted by ``/counts``, still served by ordinary retrieval and still carrying
every column a consumer reads its label from. The tier is computed at read
time from the journal and is not persisted anywhere.

A tier rather than a multiplicative penalty, deliberately: doc 08 §6's state
diagram gives ``stale_labelled`` as a state reached from ``open``, and with
the column ruled out the only faithful rendering of a *state* is a categorical
rank key. A penalty factor would leave "drops off the active queue" as a
probabilistic claim — a hot enough stale dispute would still outrank fresh
work — while the tier makes it exact, and consequence ordering still applies
in full **within** each tier.

**The clock is the dispute's onset, read from the journal.** The fact row
carries no ``disputed_at`` (adding one is a baseline regeneration, which
serialises through one owner per epic), so the timestamp comes from the
``verified`` event whose payload records the transition *into* ``disputed``.
Two spellings were rejected: ``knowledge_triples.created_at`` decays a fresh
dispute on a year-old fact on day one, and the *latest* ``verified`` event
never advances at all for a fact whose contradiction is re-affirmed on every
scan pass (that hold journals a row with ``before == after == disputed``,
which the onset predicate excludes for exactly this reason). A fact with no
journalled onset — a legacy or hand-seeded row — is treated as **not stale**:
failing to decay costs the human one glance, wrongly decaying pushes an item
out of the tier they are looking at, and this layer's direction of error is to
under-claim.

**Cost at scale.** Every derivation is scoped to the open set by the leading
``open_facts`` CTE, which is exactly ``ix_knowledge_triples_review``'s own
partial predicate — so nothing here is per-fact-in-the-table. At 100k facts
with a human-sized backlog of, say, 500 open rows, a page costs: one partial
index scan yielding 500 rows; one index-driven pass over ``fact_sources``
(``ix_fact_sources_fact``) for those 500; one hash/index join into
``memory_access_stats`` on its primary key; two index probes per open subject
into ``entity_relations`` (its UNIQUE's source prefix and
``ix_entity_relations_target``); and one ``ix_events_object`` probe per open
**dispute** only — the events lateral never runs for a non-disputed open row.
The sort is over the open set, not the table. What does not scale is a backlog
that is itself unbounded, and that is the failure doc 08 §6 chose a
self-pruning status flag plus this decay to prevent.

``memory_access_stats`` is reached by casting ``fact_sources.source_ref`` to
``uuid``, and the guards on that cast are of two different strengths — stated
separately, because a guard nobody has tried to break is a guard nobody has
tested.

*The canonical-shape regex is load-bearing, and measured to be.* ``source_ref``
holds every kind's spelling, and nothing on disk stops a **memory**-kind row
carrying a ref ``memory_source_ref`` never minted. Removing the ``~``
predicate makes the whole triage query raise
``InvalidTextRepresentationError`` on the first such row — verified by
deleting it and watching
``test_a_memory_ref_that_is_not_a_uuid_is_invisible_rather_than_fatal`` fail
with exactly that error. A ref this module cannot interpret is left invisible
instead, which is the same conservative reading
``fact_provenance.reap_orphaned_memory_sources`` already applies to it.

*The ``AS MATERIALIZED`` fence is defence in depth, and is not claimed as
more.* ``AND`` is not evaluation order, so in principle a planner free to
inline the CTE could hoist the cast above the ``source_kind`` filter and abort
on a ``human``-kind ref — the trap ``fact_provenance._ORPHANED_PROVENANCE``
documents. Dropping the fence was tried, and on PostgreSQL 17 with this
statement's shape the planner kept the filter below the cast anyway, so no
test in this suite distinguishes the two. It stays because the hazard is real
and the fence is free, not because anything here proves it fires.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config

# Imported rather than re-typed. `MEMORY_SOURCE_KIND` and the canonical ref
# shape are one contract with two readers now: the withdrawal sweep that
# deletes provenance and this ranking that reads it. Two spellings of the same
# convention would drift silently — a ref this module could not match would
# score zero heat with no error and no symptom, which is the failure that
# module's own docstring exists to prevent.
from app.services.fact_provenance import (
    MEMORY_SOURCE_KIND,
    _CANONICAL_REF as CANONICAL_MEMORY_REF,
)

logger = logging.getLogger(__name__)

REVIEW_QUEUE_CONFIG_KEY = "review_queue"

# 30 days, and the number is chosen from what it costs to be wrong in each
# direction. Decay is non-destructive — the fact stays disputed, queued and
# served labelled — so being early costs the maintainer one extra glance at a
# second tier, while being late costs them a backlog whose head never moves.
# That asymmetry argues for the shorter end. Against going shorter still: a
# solo maintainer triaging weekly needs an item to survive several passes
# before "left unreviewed" is a fair description of it, and four consecutive
# untouched passes is real evidence they are not going to act on it. 90 (the
# supersession window) is the wrong neighbour to copy — that window bounds
# when two memories may be *about* the same thing, not how long a human takes.
DEFAULT_DISPUTE_STALE_DAYS = 30

# The half-life of an access when it is read as heat. At 30 days a fact last
# hit a year ago retains 2**-12 of its count — dormant, in doc 08's word —
# while last week's traffic is still worth ~85% of itself, so the arm tracks
# the working set rather than lifetime popularity.
DEFAULT_ACCESS_HALF_LIFE_DAYS = 30

# Both arms' weights are constants, not config. They encode a *policy* doc 08
# §6 already fixes (retrieval frequency is named first, and it is the arm
# measured from real agent behaviour rather than derived from graph shape), and
# the repository's rank-arm discipline is that a weight moves on a measured
# retrieval win recorded in the gate ledger, never on intuition. Exposing them
# as an operator-editable row would invite exactly the untracked retune that
# discipline exists to forbid; a retune here is a code change with a ledger
# entry behind it.
W_RETRIEVAL_FREQUENCY = 1.0
W_SUBJECT_SALIENCE = 0.5

_PARAM_BOUNDS: dict[str, tuple[int, int]] = {
    "dispute_stale_days": (1, 3650),
    "access_half_life_days": (1, 3650),
}

_PARAM_DEFAULTS: dict[str, int] = {
    "dispute_stale_days": DEFAULT_DISPUTE_STALE_DAYS,
    "access_half_life_days": DEFAULT_ACCESS_HALF_LIFE_DAYS,
}

STALE_TIER = 0
ACTIVE_TIER = 1

STALE_LABEL = "stale_labelled"
ACTIVE_LABEL = "active"


@dataclass(frozen=True)
class RankingConfig:
    """The two operator-tunable numbers, already validated."""

    dispute_stale_days: int = DEFAULT_DISPUTE_STALE_DAYS
    access_half_life_days: int = DEFAULT_ACCESS_HALF_LIFE_DAYS


DEFAULT_RANKING_CONFIG = RankingConfig()


async def get_ranking_config(session: AsyncSession) -> RankingConfig:
    """The effective ranking parameters: merge over defaults, validate, clamp.

    **One row read per query, never per item, and deliberately uncached.** The
    read is a primary-key lookup on ``config`` issued once per list call,
    alongside the two statements the call already makes; the per-item cost is
    zero because the value is interpolated into the one ranking statement, not
    consulted per row. A TTL cache (the ``feature_flags`` pattern) is the wrong
    trade here: the queue is a human-rate surface, so the cache would save a
    negligible round trip while introducing a window in which an operator who
    just changed ``dispute_stale_days`` reloads the page and sees no effect —
    a setting that appears not to work is worse than a setting that costs one
    index lookup. If this surface ever gains a polling client, the read is the
    single place to revisit and the cache invalidation would be "on write to
    the ``review_queue`` config row", which has no writer today.

    The row is operator-edited with no schema in front of it, so every
    malformed shape degrades loudly rather than raising: an unknown key is
    ignored with a warning naming it, a non-integer value falls back to its
    default, and an out-of-range value is clamped. A bad row must not take the
    triage screen down.
    """
    result = await session.execute(
        select(Config).where(Config.key == REVIEW_QUEUE_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    raw = row.value if row is not None and isinstance(row.value, dict) else {}

    for key in raw:
        if key not in _PARAM_DEFAULTS:
            logger.warning(
                "%s config row carries unknown key %r; ignoring. Known keys: %s",
                REVIEW_QUEUE_CONFIG_KEY,
                key,
                sorted(_PARAM_DEFAULTS),
            )

    values: dict[str, int] = {}
    for name, default in _PARAM_DEFAULTS.items():
        if name not in raw:
            values[name] = default
            continue
        candidate = raw[name]
        # bool is an int subclass, and True would silently read as a one-day
        # threshold — a typo that behaves like a decision.
        if isinstance(candidate, bool) or not isinstance(candidate, int):
            logger.warning(
                "%s.%s is %r, not an integer; falling back to the default %d",
                REVIEW_QUEUE_CONFIG_KEY,
                name,
                candidate,
                default,
            )
            values[name] = default
            continue
        low, high = _PARAM_BOUNDS[name]
        if candidate < low or candidate > high:
            clamped = min(max(candidate, low), high)
            logger.warning(
                "%s.%s is %d, outside [%d, %d]; clamping to %d",
                REVIEW_QUEUE_CONFIG_KEY,
                name,
                candidate,
                low,
                high,
                clamped,
            )
            values[name] = clamped
            continue
        values[name] = candidate

    return RankingConfig(**values)


# The columns the ranking adds to each open-fact row. Named once so the query
# builder and the explanation builder cannot disagree about the shape.
RANKING_COLUMNS = (
    "source_memories",
    "peak_access_count",
    "last_accessed",
    "decayed_access",
    "neighbour_count",
    "disputed_at",
    "dispute_age_days",
    "frequency_component",
    "salience_component",
    "consequence_score",
    "active_tier",
)

# Every knob is interpolated as a SQL *literal* rather than bound, for the same
# reason `review_state = 'open'` is: the planner sees the constant, and the
# statement the EXPLAIN proof runs stays byte-identical to the one production
# executes with the same config. Each value is coerced through int()/float()
# at the interpolation site, so there is no string reaching the SQL text.
_RANKED_FACTS_TEMPLATE = """
WITH open_facts AS MATERIALIZED (
    SELECT {inner_columns}
    FROM knowledge_triples
    WHERE {where_sql}
),
memory_sources AS MATERIALIZED (
    SELECT fs.fact_id, fs.source_ref
    FROM fact_sources fs
    JOIN open_facts o ON o.id = fs.fact_id
    WHERE fs.source_kind = '{memory_kind}'
      AND fs.source_ref ~ '{canonical_ref}'
),
frequency AS (
    SELECT ms.fact_id,
           COUNT(*) AS source_memories,
           MAX(mas.access_count) AS peak_access_count,
           MAX(mas.last_accessed) AS last_accessed,
           MAX(
               mas.access_count * power(
                   0.5,
                   GREATEST(
                       0.0,
                       CAST(EXTRACT(EPOCH FROM (now() - mas.last_accessed))
                            AS double precision)
                   ) / {half_life_seconds}
               )
           ) AS decayed_access
    FROM memory_sources ms
    JOIN memory_access_stats mas ON mas.memory_id = CAST(ms.source_ref AS uuid)
    GROUP BY ms.fact_id
),
salience AS (
    SELECT o.id AS fact_id, COUNT(DISTINCT n.neighbour_id) AS neighbour_count
    FROM open_facts o
    JOIN LATERAL (
        SELECT r.target_entity_id AS neighbour_id
        FROM entity_relations r
        WHERE r.source_entity_id = o.subject_id
          AND r.target_entity_id <> o.subject_id
        UNION ALL
        SELECT r.source_entity_id AS neighbour_id
        FROM entity_relations r
        WHERE r.target_entity_id = o.subject_id
          AND r.source_entity_id <> o.subject_id
    ) n ON TRUE
    WHERE o.subject_id IS NOT NULL
    GROUP BY o.id
),
dispute AS (
    SELECT o.id AS fact_id, ev.created_at AS disputed_at
    FROM open_facts o
    JOIN LATERAL (
        SELECT e.created_at
        FROM events e
        WHERE e.object_type = 'fact'
          AND e.object_id = o.id
          AND e.event_type = 'verified'
          AND e.payload->'after'->>'verification_status' = 'disputed'
          AND COALESCE(e.payload->'before'->>'verification_status', '') <> 'disputed'
        ORDER BY e.created_at DESC
        LIMIT 1
    ) ev ON TRUE
    WHERE o.verification_status = 'disputed'
)
SELECT {outer_columns},
       CAST(COALESCE(f.source_memories, 0) AS integer) AS source_memories,
       CAST(COALESCE(f.peak_access_count, 0) AS integer) AS peak_access_count,
       f.last_accessed AS last_accessed,
       CAST(COALESCE(f.decayed_access, 0.0) AS double precision) AS decayed_access,
       CAST(COALESCE(s.neighbour_count, 0) AS integer) AS neighbour_count,
       d.disputed_at AS disputed_at,
       CAST(EXTRACT(EPOCH FROM (now() - d.disputed_at)) / 86400.0
            AS double precision) AS dispute_age_days,
       CAST({w_frequency} * ln(1.0 + COALESCE(f.decayed_access, 0.0))
            AS double precision) AS frequency_component,
       CAST({w_salience} * ln(1.0 + CAST(COALESCE(s.neighbour_count, 0) AS double precision))
            AS double precision) AS salience_component,
       CAST({w_frequency} * ln(1.0 + COALESCE(f.decayed_access, 0.0))
            + {w_salience} * ln(1.0 + CAST(COALESCE(s.neighbour_count, 0) AS double precision))
            AS double precision) AS consequence_score,
       CASE
           WHEN d.disputed_at IS NOT NULL
                AND d.disputed_at < now() - ({stale_days} * INTERVAL '1 day')
           THEN {stale_tier} ELSE {active_tier}
       END AS active_tier
FROM open_facts o
LEFT JOIN frequency f ON f.fact_id = o.id
LEFT JOIN salience s ON s.fact_id = o.id
LEFT JOIN dispute d ON d.fact_id = o.id
ORDER BY {order_sql}
LIMIT :limit OFFSET :offset
"""


def build_ranked_facts_sql(
    *,
    column_names: tuple[str, ...],
    where_sql: str,
    order_sql: str,
    config: RankingConfig,
) -> str:
    """The consequence-ranked open-facts statement.

    ``where_sql`` is the caller's membership predicate verbatim and is applied
    to ``knowledge_triples`` inside the leading CTE, unwidened — the ranking
    changes the ``ORDER BY`` and the projection, never which rows are members.
    """
    inner_columns = ", ".join((*column_names, "subject_id"))
    outer_columns = ", ".join(f"o.{name}" for name in column_names)
    return _RANKED_FACTS_TEMPLATE.format(
        inner_columns=inner_columns,
        outer_columns=outer_columns,
        where_sql=where_sql,
        order_sql=order_sql,
        memory_kind=MEMORY_SOURCE_KIND,
        canonical_ref=CANONICAL_MEMORY_REF,
        half_life_seconds=f"{float(config.access_half_life_days) * 86400.0:.1f}",
        stale_days=int(config.dispute_stale_days),
        w_frequency=f"{float(W_RETRIEVAL_FREQUENCY):.6f}",
        w_salience=f"{float(W_SUBJECT_SALIENCE):.6f}",
        stale_tier=int(STALE_TIER),
        active_tier=int(ACTIVE_TIER),
    )


def consequence_explanation(row: dict[str, Any], config: RankingConfig) -> dict[str, Any]:
    """The per-item rationale that rides the response beside the score.

    Doc 08 §6's ranking has to be answerable per item — "why is this here, and
    why above that one" — so every input that moved the score is carried, not
    just the total. A bare float would be unauditable: the maintainer could
    not tell a hot fact from a hub-subject fact, and neither could anyone
    diagnosing a ranking that looked wrong.
    """
    tier = int(row["active_tier"])
    stale = tier == STALE_TIER
    age_days = row["dispute_age_days"]
    return {
        "score": float(row["consequence_score"]),
        "tier": tier,
        "retrieval_frequency": {
            "source_memories": int(row["source_memories"]),
            "peak_access_count": int(row["peak_access_count"]),
            "last_accessed": row["last_accessed"],
            "decayed_access": float(row["decayed_access"]),
            "half_life_days": config.access_half_life_days,
            "weight": W_RETRIEVAL_FREQUENCY,
            "component": float(row["frequency_component"]),
        },
        "subject_salience": {
            "neighbour_count": int(row["neighbour_count"]),
            "weight": W_SUBJECT_SALIENCE,
            "component": float(row["salience_component"]),
        },
        "staleness": {
            "stale": stale,
            "label": STALE_LABEL if stale else ACTIVE_LABEL,
            "dispute_opened_at": row["disputed_at"],
            "dispute_age_days": None if age_days is None else float(age_days),
            "threshold_days": config.dispute_stale_days,
        },
    }

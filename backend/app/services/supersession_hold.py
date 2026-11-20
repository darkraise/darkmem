"""The supersession-signal promotion blocker — spec §2.1 condition 4's other half.

Doc 08 §4.1 (as amended) and spec §2.1 make promotion conditional on two
independent things being absent: an open contradiction (``contradiction_veto``,
T2.04) and **a newer REPLACES-family / supersession signal standing over the
fact's live memory sources**. Doc 08 dropped the second by drift rather than by
decision; the Tier-3 ruling of 2026-07-29
(``.superpowers/sdd/rulings/2026-07-29-t2.03-supersession-blocker.md``) restored
it and minted T2.60 to own it. This module is that ruling's only expression.

**It is a hold and nothing else.** It never writes ``disputed`` -- a superseded
source is *staleness*, not a dispute, and there are no "both sides" to serve --
and it never demotes an already-``corroborated`` fact. It only withholds a
promotion that would otherwise fire. Everything here is one indexed SQL read:
deterministic, no model call, no configuration, reproducible on replay.

## The predicate, and why each word of it is what it is

*A fact is blocked when at least one of its ``memory``-kind ``fact_sources``
rows names a memory whose ``status`` is ``'superseded'`` under a strictly newer
superseder.*

**The applied status, not the asserted edge.** ``memories.status`` and a
REPLACES-family ``entity_relations`` edge are two different signals: the edge is
what some memory *asserted*, the status is what ``detect_supersessions``
*applied* after putting that assertion through six guards -- same project, the
candidate still active, a ``technologies`` overlap, a 90-day window, a
strictly-older ordering with an id tie-break, and the per-target speculative
gate. Reading the raw edge would inherit none of them. The speculative gate is
the one that matters most here: it exists so "we might switch to X" supersedes
nothing, and a blocker keyed off the edge would hold a fact's promotion on a
replacement nobody has made. So this module reads the column, and the six guards
are inherited rather than re-implemented. It follows that this blocker cannot
fire where the memory-side detector declined to, which is the correct coupling:
one definition of "superseded" in the codebase, not two that drift.

**"Newer" means newer than the source memory, never newer than the fact.**
The tempting reading -- compare the superseder against the fact's ``created_at``
-- has a hole, because facts are minted by ``fact_lift`` on a cadence rather
than at capture time. A supersession that lands *before* the lift would then
leave the fact unblocked: its sources are superseded, yet every supersession
predates it. Since supersession strips no Layer-1 graph contributions (doc 08
§3.3; the withdrawal sweep fires on re-extraction or deletion, and supersession
is neither), that fact still lifts and would promote on already-replaced
evidence -- exactly the failure the ruling constructs. Anchoring "newer" to the
*source memory* has no such ordering dependency.

Against the source memory the comparison is, today, structurally guaranteed:
``detect_supersessions``' fifth guard already requires the superseder be
strictly newer with an id tie-break, so it is spelled here as the same
comparison rather than a different one. It is still checked rather than
assumed, because ``memories.status`` has a second future writer -- doc 08
§3.4's status bridge (T2.45) -- whose guards are about *fact invalidation* and
say nothing about timestamps. A row this module cannot show a newer superseder
for is not treated as a supersession signal.

**Any superseded source, not all of them, and not a same-claim test.** Two
refinements were available and both are refused for the same reason. Requiring
*every* source to be superseded, or requiring the superseding memory to concern
the fact's own endpoints, each narrows the block -- and narrowing a *hold* moves
the error in the forbidden direction. Doc 08 §5.3 fixes the asymmetry for this
whole subsystem ("undercounting ... only *delays* catching a contradiction (the
preferred failure); it never manufactures one"), and spec §2.1 states it as
doctrine: "a delayed promotion costs a label (candidates are served, labeled,
above nothing); a wrong promotion costs every article that cites it and every
agent that propagates it". For a blocker the mapping is: over-blocking delays a
promotion, the preferred failure; under-blocking mints a ``corroborated`` badge
over evidence the store already knows was replaced, the worst one. The ruling
reaches the same place and says so -- "the broad predicate is the default
because over-blocking is under-claiming, the safe direction" -- and permits
refinement "only toward precision it can defend". Neither refinement is
defensible on measurement that exists today, so neither ships.

The cost is real and is stated rather than hidden: a fact sourced by one
superseded memory and one live one is held even though the live source asserts
it independently, and because supersession is monotonic the hold does not lift
on its own. That is a *delayed promotion on a served, labelled candidate*, and
it is visible -- the journal carries ``supersession_blocked`` on every such
decision, so T2.40 can measure how often it fires and argue a refinement from
the number instead of from intuition.

**No relation type is read here at all.** The taxonomy discipline that caught
T2.04 -- ``LEGACY_RELATION_TYPE_MAP`` folds ``VISITED`` and ``LIVES_IN`` onto
``HAPPENED_ON``, so a set keyed on a stored ``rel_type`` silently acquires
members nobody added -- does not reach this module, because the REPLACES family
is consulted on the memory side by ``supersession.is_supersession_trigger``
(through ``family_key``, which already folds the legacy ``BUILDS_ON``) and never
here. This module keys off a status column and a pointer, so there is no set to
widen and nothing for that map to rewrite underneath it.

## What a mis-spelled ``source_ref`` does, and why there is no filter for it

The join is ``CAST(memories.id AS text) = fact_sources.source_ref``, the cast
direction ``fact_provenance`` establishes: the ref column holds every kind's
spelling, and a planner free to hoist ``CAST(source_ref AS uuid)`` above the
kind filter would abort on the first non-uuid ref.

``fact_provenance``'s backstop additionally filters refs to ``_CANONICAL_REF``,
and it is important that this module does **not** copy that filter, because the
two queries have opposite shapes. The backstop is an anti-join where failing to
match means *deletion*, so an uninterpretable ref must be excluded to spare it.
This is a positive join where failing to match means *not blocking*, so the
filter would be strictly redundant: ``CAST(uuid AS text)`` renders exactly the
canonical spelling, so every ref that could match the join already matches the
regex. Adding it would be a predicate that reads like a guard while deciding
nothing -- and an inert guard is worse than none, because a reader trusts it.

The consequence is a real limitation, shared with the withdrawal sweep and
bounded the same way: a memory-kind ref not spelled the way
``memory_source_ref`` mints one is invisible here, so a fact sourced only
through such a ref promotes unblocked. The direction of that error is the
unsafe one, unlike the backstop's, and the mitigation is upstream --
``memory_source_ref`` is the single minter of the spelling. It is recorded here
rather than papered over with a filter that cannot fix it.

## The denominator ruling (T2.40 and T2.51 read this)

**A supersession-blocked hold belongs in the promotion-rate denominator.**

T2.51's runner derives "eligible" as *a journaled transition out of ``candidate``
whose bar was already met*, implemented as ``outcome IN ('promote', 'dispute')``
with ``origin_count >= required_n``. That equivalence held only while no code
path returned a hold for a candidate that met its bar. This blocker is exactly
that path, so the equivalence has to be restated rather than inherited:

    eligible == a journaled decision on a fact whose bar was met, out of
                ``candidate`` -- whether it promoted, was vetoed to
                ``disputed``, or was held by the supersession blocker.

so the runner's filter becomes ``outcome IN ('promote', 'dispute') OR (outcome
= 'hold' AND supersession_blocked)``, with the blocked count reported as its own
labelled column beside ``promoted`` and ``eligible``.

The alternative -- calling a blocked fact "not eligible" and dropping it from
the denominator -- is refused, and the reason is the one T2.06's ruling already
gave: a widening block would then remove facts from the denominator instead of
from the numerator, so the measured promotion rate would stay flat (or rise)
while fewer facts actually promoted. That is a tuning distortion with no trace
in the journal, and "do not resolve this by omission" is the corpus's own
language for it. Inclusion makes the block cost visible in the rate; the
separate blocked count is what lets T2.40 still isolate the effect of N, since
subtracting a reported number is always available while recovering a number that
was never counted is not.

**Tier-C only (invariant 15).** This is an input to the verification ladder and
inherits its confinement: nothing in capture or retrieval may reach it. The
guard is this module's **own** tree-wide source scan,
``test_no_app_code_outside_the_ladder_reaches_the_blocker`` in
``tests/test_supersession_blocker.py``, whose allowlist is the ladder alone.
The ladder's own scan does not cover this: it matches imports of the ladder
module and its applier entry point, so a capture path importing
``adjudicate_supersession_hold`` directly would trip nothing there. Each Tier-C
input therefore carries its own scan, as ``contradiction_veto`` does.

(The applier's name is deliberately not spelled here. That scan reads whole
lines and skips only ``#`` comments, so naming it inside a docstring in a
non-allowlisted module registers as a reference and fails the build — which is
how this paragraph's first draft was caught.)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.fact_provenance import (
    _CANONICAL_REF as CANONICAL_MEMORY_REF,
    MEMORY_SOURCE_KIND,
)

logger = logging.getLogger(__name__)

# One row is enough to block, so the scan stops at the first. The ORDER BY makes
# the pick stable when several sources qualify, rather than leaving it to plan
# choice. **No test pins which row is chosen**, and none is claimed: the boolean
# the ladder consumes is identical either way, so the ordering is tidiness for a
# human reading two runs side by side, not a property anything depends on.
_SUPERSEDED_SOURCE_SQL = text("""
    SELECT fs.source_ref AS memory_ref,
           CAST(m.superseded_by AS text) AS superseder_ref
    FROM fact_sources fs
    JOIN memories m ON m.id = CASE
        WHEN fs.source_ref ~ CAST(:canonical AS text)
        THEN CAST(fs.source_ref AS uuid)
    END
    JOIN memories sup ON sup.id = m.superseded_by
    WHERE fs.fact_id = CAST(:fact_id AS uuid)
      AND fs.source_kind = CAST(:kind AS text)
      AND m.status = 'superseded'
      AND (
          sup.created_at > m.created_at
          OR (sup.created_at = m.created_at AND sup.id > m.id)
      )
    ORDER BY fs.id
    LIMIT 1
""")


@dataclass(frozen=True)
class SupersessionHold:
    """One blocking signal, and the two rows that produced it.

    **The two refs have no production consumer today**, and that is recorded
    rather than dressed up: only the boolean reaches ``decide``, and only the
    boolean rides the journal payload, so the traceability these fields offer
    is available to a caller re-running the detector (a human triaging a held
    fact) and nowhere else. ``ContradictionFinding`` is carried through to a
    journalled ``counterpart_id`` by T2.64; nothing analogous is planned here,
    so do not read this shape as a promise that the journal explains *which*
    source blocked.

    They are carried in the spelling ``memory_source_ref`` mints so a caller
    that does read them can line them up with the ``sources_changed`` payloads
    for the same memory.
    """

    fact_id: str
    memory_ref: str
    superseder_ref: str


async def detect_supersession_hold(
    session: AsyncSession, fact_id: UUID | str
) -> SupersessionHold | None:
    """Does a newer supersession signal stand over this fact's memory sources?

    ``None`` means no memory source of this fact is superseded under a newer
    superseder. Unlike the contradiction verdict this needs no third value:
    that one is tri-state because ``False`` is permission to *leave*
    ``disputed``, and silence must not resolve a dispute. This signal resolves
    nothing -- it only withholds a promotion -- so "no signal" and "no scan"
    have the same consequence and collapsing them loses nothing.

    Single detector, and deliberately not a registry tuple like
    ``CONTRADICTION_DETECTORS``. That tuple exists because recovery out of
    ``disputed`` is conjunctive over detectors, so a scan reporting through a
    side channel could resolve a dispute it cannot see. Nothing here is
    conjunctive, and a one-member registry with no second member planned is the
    zero-writer scaffolding invariant 23 forbids.
    """
    result = await session.execute(
        _SUPERSEDED_SOURCE_SQL,
        {
            "fact_id": str(fact_id),
            "kind": MEMORY_SOURCE_KIND,
            "canonical": CANONICAL_MEMORY_REF,
        },
    )
    row = result.mappings().first()
    if row is None:
        return None
    return SupersessionHold(
        fact_id=str(fact_id),
        memory_ref=row["memory_ref"],
        superseder_ref=row["superseder_ref"],
    )


async def adjudicate_supersession_hold(
    session: AsyncSession, fact_id: UUID | str
) -> bool:
    """Is this fact's promotion blocked by a supersession signal?"""
    return await detect_supersession_hold(session, fact_id) is not None

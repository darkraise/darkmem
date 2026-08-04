"""T2.51 — the promotion-rate metric and the false-promotion audit, over
``events`` alone (doc 17 §5.1, doc 08 §4.1-4.3).

This module is plumbing, not judgment: it produces numbers and refuses to
produce a number it cannot defend. It does not state a bar and does not
decide whether a rate is acceptable -- T2.40 (Fable, adversarial) reads what
this emits and designs the bar separately (runbook §2's standing rule).

**Sources, and why reading them satisfies "journal alone".** Doc 17 §5.1
permits the false-promotion audit to read ``knowledge_triples`` and the
review queue; the "journal alone" clause in this task's brief is about not
adding an *instrumentation side-table* -- a counter or a mirror this task
would have to write -- not about refusing the live tables the doc names.
Concretely:

- The promotion-rate metric (both slices) reads **only** ``events``. T2.06
  (``app/repositories/knowledge_triples.py:340-410``, and
  ``tests/test_ladder_journaling.py``) enriched the ``verified`` payload
  with everything the metric needs -- ``outcome``, ``origin_count``,
  ``required_n``, ``gate_fired``, ``source_kinds`` -- precisely so this
  query never has to join back to ``knowledge_triples``.
- The false-promotion audit's "later disputed" half also reads **only**
  ``events`` (a self-join, T2.06's exact SQL, reproduced here verbatim and
  pinned by ``tests/test_ladder_journaling.py``). Its "or human-rejected"
  half reads the ``human_verdict`` journal (T2.63) -- also ``events``, so
  the whole audit is one table. **It briefly read ``review_state`` and was
  structurally blind doing so:** T2.62 defines that column as pure
  queue-membership -- only ``'open'`` is writable, and resolution clears it
  to ``NULL`` -- so no value in that design ever means "rejected", the count
  read 0 forever, and its own tripwire could never fire because the
  vocabulary it watched was correct. T2.63 made the verdict an **event**,
  which is the same discipline T2.06 applied to machine transitions.
  ``KNOWN_HUMAN_VERDICTS`` now guards the verdict vocabulary instead: an
  unrecognised value means a writer bypassed ``record_human_verdict``.

**The denominator, derived, not guessed.** "Eligible candidate facts" is
*not* every candidate fact -- doc 08's ordinary holds are deliberately
unjournaled (T2.06's ruling: an unblocked candidate below its bar "was
never eligible... by construction, not by omission"), so those rows do not
exist to count. ``decide()``'s own docstring (``app/services/
verification_ladder.py``) and ``test_ladder_journaling.py``'s
``TestGCMetricsFromEventsAlone`` establish the equivalence this module
relies on: **eligible == a journaled transition out of ``candidate`` with
``origin_count >= required_n``** -- i.e. ``outcome IN ('promote',
'dispute')`` with the bar already met. That equivalence holds only because
no code path today returns a *hold* for a candidate that met its bar; T2.60
(the supersession blocker) is defined to break it by design, which is why
``validate_verified_events`` below refuses to run past a payload shape it
cannot yet account for rather than silently mis-sizing the denominator.

**The T2.60 / unknown-vocabulary guard.** ``decide()``'s docstring records
an argued ruling: T2.60 must journal its own ``supersession_blocked`` field
on a hold exactly the way ``contradiction_blocked`` does today, "because the
alternative lets a widening block silently inflate the promotion rate with
no trace." T2.60 has not landed, so no payload carries that field yet --
this module's job is not to implement it, only to make sure a payload that
does can never be silently mis-bucketed. ``validate_verified_events`` closes
that door three ways: an unrecognised ``outcome``, an unrecognised
``gate_fired``, or an unrecognised payload key (which is exactly what a new
``supersession_blocked`` field would be) all raise ``UnrecognisedPayloadError``
before any metric is computed. The fourth check -- a ``hold`` outcome that is
not ``contradiction_blocked`` -- is the concrete shape T2.60's hold will take
the day it lands: today's code never journals that combination (only a
contradiction-blocked hold journals at all), so seeing one means a new hold
reason has started writing and the denominator above needs to change before
its number can be trusted. A fifth check closes a narrower but adjacent gap:
a status-changing row (``before`` and ``after`` disagree) carrying no
``outcome`` at all is invisible to every eligibility filter this module's
SQL uses and would otherwise vanish from both the numerator and the
denominator with no trace.

**A field this runner validates but never counts (T2.64).** The ``verified``
payload now carries the contradiction's counterpart -- doc 08 §6's "labelled
with both sides", recorded on the row because the finding is in scope only
inside the ladder and no surface may re-derive it. It is validated on the same
closed-vocabulary terms as every key above, *including its nested keys*,
because an unvalidated blob inside a validated payload is the same hole one
level down. It changes no number: the decision it explains is already fully
described by ``outcome`` and ``contradiction_blocked``, both of which the SQL
below already reads, so no denominator, numerator or slice moves on its
account. Its ``enumeration`` field is the one thing a reader must not
misinterpret -- it says the block names the counterpart the verdict turned on,
never the complete set -- so an unknown value there fails loud rather than
reading as the old claim.

**The blast radius of one bad payload is the whole window, on purpose.**
``validate_window`` runs before any metric query, so a single unrecognised
``verified`` payload anywhere in ``[since, now)`` fails the entire run --
not just the bucket it would have landed in -- for as long as that payload
stays inside the window (up to ``window_days``). This is a stated
trade-off, not an oversight: a metric that silently drops the one row it
cannot classify is exactly the failure mode this module exists to refuse.
The remediation when it happens is to widen the vocabulary above (add the
new outcome/key/state to the relevant ``KNOWN_*`` set, or implement the
arm it represents) and re-derive the denominator query if the new shape
changes what "eligible" means -- never to catch and skip the offending row.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ─────────────────────── the closed vocabularies this runner knows ───────────────────────

# The one outcome that is NOT an `Outcome` of the ladder: T2.05's
# human ratification journals it from
# `KnowledgeTripleRepository.ratify`, which is a different writer with a
# different decision behind it. It is listed so the row can be *bucketed*
# rather than raising, and it is deliberately inert in every metric below:
#
#   - The promotion-rate denominator filters `outcome IN ('promote', 'dispute')`
#     (plus T2.60's blocked hold), so a ratify never enters it. That is the
#     correct arithmetic, not an oversight -- G-C measures the machine ladder's
#     promotion rate, and counting a human's imprimatur in it would report the
#     reviewer's diligence as the machine's accuracy.
#   - The false-promotion audit anchors on `after.verification_status =
#     'corroborated'`; a ratify's after-state is `confirmed`, so it anchors
#     nothing.
#   - A ratify payload carries no `origin_count`/`required_n` (there is no bar
#     to meet), so the `>=` predicate is NULL for it and filters it out even
#     before the outcome test.
RATIFY_OUTCOME = "ratify"

# The five ladder outcomes are app.services.verification_ladder.Outcome,
# restated here rather than imported: this module must keep working (and keep
# *validating*) even if the app package is unavailable to a bare read-only
# probe process, and a closed vocabulary a metrics runner checks against should
# be spelled where the check lives, not silently inherited from a type alias
# that could widen without this file noticing.
KNOWN_OUTCOMES = frozenset(
    {"promote", "demote", "hold", "dispute", "recover", RATIFY_OUTCOME}
)

# app.repositories.fact_sources.OriginProfile.gate_fired_for's three values.
KNOWN_GATE_FIRED = frozenset({"diversity", "time_gap", "none"})

# The full key set set_verification_status writes into a `verified` payload
# when `outcome` is given (app/repositories/knowledge_triples.py:450-467).
KNOWN_PAYLOAD_KEYS = frozenset({
    "before", "after", "outcome", "origin_count", "required_n",
    "gate_fired", "source_kinds", "contradiction_blocked", "confidence",
    # T2.60's deterministic promotion blocker. Journaled per the T2.06
    # ruling in verification_ladder.decide's docstring: a widening block
    # that did not journal would silently inflate the promotion rate with
    # no trace, so the flag rides the payload and is counted below.
    "supersession_blocked",
    # T2.64's contradiction counterpart -- doc 08 Section 6's "labelled with
    # both sides", recorded where the finding is in scope because nothing
    # else may re-derive it. It carries **no** eligibility signal: the
    # decision it explains is already fully described by `outcome` and
    # `contradiction_blocked`, both of which this runner's SQL already
    # reads, so no denominator, numerator or slice changes on its account.
    # It is validated rather than ignored because an unvalidated nested blob
    # is precisely the vocabulary hole this module exists to refuse.
    "contradiction",
})

# The counterpart block's own closed vocabulary
# (app.services.verification_ladder.contradiction_evidence). Nested keys are
# checked on the same terms as top-level ones: a block that grew a field would
# otherwise pass this runner untouched, which is the silent widening
# KNOWN_PAYLOAD_KEYS exists to make impossible one level up.
KNOWN_CONTRADICTION_KEYS = frozenset({
    "counterpart_id", "counterpart_subject", "counterpart_rel_type",
    "counterpart_object", "rule", "witness_origin", "enumeration",
})

# How many contradictions the block claims to name. `first_finding` is the
# counterpart the verdict turned on, not the complete set -- the adjudication
# short-circuits at the first detector that finds anything. A new value here
# means that selection rule changed, which changes what a reader of this
# payload is entitled to conclude, so it fails loud rather than reading as the
# old claim.
KNOWN_ENUMERATIONS = frozenset({"first_finding"})


# Below this many observations, one additional data point swings the
# reported rate by more than 20 percentage points (1/5 = 0.20) -- too coarse
# for the bucket to carry any signal either way. This is a *reporting*
# floor ("say so, don't hide it"), not a measurement bar; T2.40 owns the bar.
UNDER_POWERED_THRESHOLD = 5


class UnrecognisedPayloadError(RuntimeError):
    """A `verified` event (or a `review_state` value) carries something this
    runner does not know how to bucket.

    Raised instead of silently falling through to a default bucket, per the
    T2.60 ruling in `verification_ladder.decide`'s docstring: a denominator
    built by enumerating known hold reasons must fail loudly on an unknown
    one, because the concrete hazard -- a meets-bar-but-holds fact that the
    current `outcome IN ('promote', 'dispute')` eligibility filter cannot
    see -- silently shrinks the denominator with no trace.
    """


def validate_verified_event_payload(payload: dict, *, event_id: object) -> None:
    unknown_keys = set(payload) - KNOWN_PAYLOAD_KEYS
    if unknown_keys:
        raise UnrecognisedPayloadError(
            f"verified event {event_id} carries unrecognised payload key(s) "
            f"{sorted(unknown_keys)} -- a new field (e.g. T2.60's "
            f"'supersession_blocked') has started journaling and this "
            f"runner's eligibility/denominator logic has not been updated "
            f"for it. Known keys: {sorted(KNOWN_PAYLOAD_KEYS)}"
        )
    outcome = payload.get("outcome")
    if outcome is not None and outcome not in KNOWN_OUTCOMES:
        raise UnrecognisedPayloadError(
            f"verified event {event_id} carries unrecognised outcome "
            f"{outcome!r}; known outcomes are {sorted(KNOWN_OUTCOMES)}"
        )
    gate_fired = payload.get("gate_fired")
    if gate_fired is not None and gate_fired not in KNOWN_GATE_FIRED:
        raise UnrecognisedPayloadError(
            f"verified event {event_id} carries unrecognised gate_fired "
            f"{gate_fired!r}; known values are {sorted(KNOWN_GATE_FIRED)}"
        )
    contradiction = payload.get("contradiction")
    if contradiction is not None:
        if not isinstance(contradiction, dict):
            raise UnrecognisedPayloadError(
                f"verified event {event_id} carries a 'contradiction' that is "
                f"{type(contradiction).__name__}, not an object; the counterpart "
                f"block is a mapping of {sorted(KNOWN_CONTRADICTION_KEYS)}"
            )
        unknown_inner = set(contradiction) - KNOWN_CONTRADICTION_KEYS
        if unknown_inner:
            raise UnrecognisedPayloadError(
                f"verified event {event_id} carries unrecognised contradiction "
                f"key(s) {sorted(unknown_inner)}; known keys are "
                f"{sorted(KNOWN_CONTRADICTION_KEYS)}"
            )
        if not contradiction.get("counterpart_id"):
            raise UnrecognisedPayloadError(
                f"verified event {event_id} carries a 'contradiction' block "
                f"with no counterpart_id -- a dispute that names no counterpart "
                f"is the state doc 08 Section 6 exists to end, and a block that "
                f"cannot be traced back to a fact is worse than none"
            )
        enumeration = contradiction.get("enumeration")
        if enumeration not in KNOWN_ENUMERATIONS:
            raise UnrecognisedPayloadError(
                f"verified event {event_id} carries contradiction enumeration "
                f"{enumeration!r}; known values are {sorted(KNOWN_ENUMERATIONS)}. "
                f"This field states how many contradictions the block names, so "
                f"an unknown value means a reader cannot tell whether it is "
                f"holding one counterpart or all of them"
            )
        # The block is produced only from a verdict that fired, so its presence
        # beside an unfired veto means a second writer -- or a stale block
        # copied onto a decision it did not describe. Both would put a live
        # dispute's evidence on a fact nothing is disputing.
        if not payload.get("contradiction_blocked", False):
            raise UnrecognisedPayloadError(
                f"verified event {event_id} carries a 'contradiction' block "
                f"while contradiction_blocked is "
                f"{payload.get('contradiction_blocked')!r}; the counterpart is "
                f"journaled only by the verdict that fired the veto, so this "
                f"row names a dispute its own evidence says did not happen"
            )
    if outcome == "hold" and not (
        payload.get("contradiction_blocked", False)
        or payload.get("supersession_blocked", False)
    ):
        raise UnrecognisedPayloadError(
            f"verified event {event_id} is a 'hold' that is not "
            f"contradiction_blocked -- today's code never journals that "
            f"shape (only a contradiction-blocked hold journals at all; see "
            f"verification_ladder.decide's T2.60 ruling). A new hold reason "
            f"has started journaling; the promotion-rate denominator must be "
            f"re-derived to account for it before this number can be trusted"
        )
    # A status-changing row with no `outcome` evidence block is invisible to
    # every eligibility filter this module's SQL uses (`outcome IN
    # ('promote', 'dispute')`) -- it would be silently excluded from both
    # the numerator and the denominator with no trace, the same genus of
    # hazard the T2.60 guard above closes for an unrecognised value. No
    # writer produces this shape today (`set_verification_status` always
    # threads the full evidence block once `outcome` is given, and every
    # real caller gives it -- see app/repositories/knowledge_triples.py's
    # docstring), but a bare-status legacy write path is a documented
    # possibility there ("every direct/legacy caller that only ever wrote a
    # bare status keeps its original two-key payload verbatim"), so this
    # checks the actual hazard (a real transition, not merely an absent
    # key) rather than assuming `outcome` is always present.
    before_status = (payload.get("before") or {}).get("verification_status")
    after_status = (payload.get("after") or {}).get("verification_status")
    if outcome is None and before_status != after_status:
        raise UnrecognisedPayloadError(
            f"verified event {event_id} changed verification_status "
            f"{before_status!r} -> {after_status!r} but carries no `outcome` "
            f"evidence block -- this runner's SQL cannot see it, so a real "
            f"promotion or dispute would be silently missing from both the "
            f"numerator and the denominator rather than merely excluded on "
            f"purpose"
        )


_VERIFIED_EVENTS_FROM_SINCE_SQL = text("""
    SELECT id, payload
    FROM events
    WHERE event_type = 'verified'
      AND object_type = 'fact'
      AND created_at >= :since
    ORDER BY created_at, id
""")


async def validate_window(session: AsyncSession, *, since: datetime) -> int:
    """Validate every `verified`/`fact` payload from `since` to now.

    Unbounded above deliberately: the false-promotion audit's "later
    disputed" check has no upper bound either (a dispute can arrive any time
    after its corroboration), so a vocabulary guard that stopped at the
    reporting window's `until` could pass over the exact payload shape the
    audit itself is about to read. Bounded below by `since` so a long-lived
    journal is not rescanned from epoch on every run (`events` is
    RANGE-partitioned by month; an unbounded scan reads every partition).

    Returns the number of payloads checked, so a validation pass over an
    empty window is visibly distinguishable from one that found nothing to
    complain about.
    """
    rows = (await session.execute(_VERIFIED_EVENTS_FROM_SINCE_SQL, {"since": since})).all()
    for event_id, payload in rows:
        validate_verified_event_payload(payload, event_id=event_id)
    return len(rows)


# ─────────────────────────────── the two metrics ───────────────────────────────

# T2.06's exact SQL (tests/test_ladder_journaling.py's _PROMOTION_RATE_SQL),
# windowed by `created_at` instead of an explicit fact-id array. "Eligible"
# is the equivalence this module's docstring derives: a journaled transition
# out of `candidate` whose bar was already met (`origin_count >= required_n`)
# when it fired, whether it promoted or was vetoed after meeting the bar.
# doc 17 §5.1's second audit half, live as of T2.63. Before it, `review_state`
# was the only candidate source and it structurally could not carry a verdict
# (T2.62 makes it pure queue membership: 'open' or NULL, no value means
# "rejected"), so this arm read 0 forever and silently. The verdict is an
# EVENT, not a state -- the same discipline T2.06 applied to machine
# transitions, which is why the whole audit is now one table.
#
# Anchored on `after.verification_status = 'corroborated'`, never on
# `outcome = 'promote'`: a fact can reach corroborated via `recover` without
# ever emitting a promote, and anchoring on the outcome made T2.06's own audit
# blind to exactly that. The `(created_at, id)` tuple compare is load-bearing
# for the same reason it is everywhere else here -- `now()` is constant within
# a transaction, so a bare `created_at >` drops same-transaction ordering.
_HUMAN_REJECTED_SQL = text("""
    SELECT COUNT(DISTINCT p.object_id) AS human_rejected
    FROM events p
    JOIN events h
      ON h.object_id = p.object_id
     AND h.event_type = 'human_verdict'
     AND h.object_type = 'fact'
     AND h.payload->>'verdict' = 'rejected'
     AND (h.created_at, h.id) > (p.created_at, p.id)
    WHERE p.event_type = 'verified'
      AND p.object_type = 'fact'
      AND p.created_at >= :since AND p.created_at <= :until
      AND p.payload->'after'->>'verification_status' = 'corroborated'
""")

# The verdict vocabulary this arm knows how to count. T2.63 raises on an
# unknown verdict at the emitter, so an unrecognised value here means a
# second writer appeared that bypassed `record_human_verdict` -- the same
# class of silent divergence KNOWN_PAYLOAD_KEYS guards for the machine side.
_HUMAN_VERDICT_VOCABULARY_SQL = text("""
    SELECT DISTINCT payload->>'verdict' AS verdict
    FROM events
    WHERE event_type = 'human_verdict'
      AND object_type = 'fact'
      AND created_at >= :since AND created_at <= :until
""")

KNOWN_HUMAN_VERDICTS = frozenset({"ratified", "regrounded", "edited", "rejected"})


_PROMOTION_RATE_BY_GATE_SQL = text("""
    SELECT
        payload->>'gate_fired' AS bucket,
        COUNT(*) FILTER (WHERE payload->>'outcome' = 'promote') AS promoted,
        COUNT(*) FILTER (
            WHERE (payload->>'supersession_blocked')::boolean
        ) AS supersession_blocked,
        COUNT(*) AS eligible
    FROM events
    WHERE event_type = 'verified'
      AND object_type = 'fact'
      AND created_at >= :since
      AND created_at <= :until
      AND payload->'before'->>'verification_status' = 'candidate'
      AND (
            payload->>'outcome' IN ('promote', 'dispute')
            -- T2.60's blocked hold is a fact that MET its bar and did not
            -- promote, which is exactly what a promotion rate measures.
            -- Excluding it would let a widening block raise the reported
            -- rate by shrinking the denominator -- the silent inflation the
            -- T2.06 ruling minted the flag to prevent.
            OR (payload->>'outcome' = 'hold'
                AND (payload->>'supersession_blocked')::boolean)
          )
      AND (payload->>'origin_count')::int >= (payload->>'required_n')::int
    GROUP BY payload->>'gate_fired'
    ORDER BY bucket
""")

# The second slice axis (brief: "by source-kind diversity", separate from
# "by which N fired" -- an aggregate over both would hide the two-sided
# argument doc 17 §5.1 makes about them). `source_kinds` is the payload's
# full per-fact kind list (all origins, not just the gate-deciding ones);
# "diverse" here means the observed kind set has more than one distinct
# value, independent of whether diversity was the gate that actually fired.
_PROMOTION_RATE_BY_DIVERSITY_SQL = text("""
    SELECT
        CASE
            WHEN (
                SELECT COUNT(DISTINCT k)
                FROM jsonb_array_elements_text(payload->'source_kinds') AS k
            ) > 1
            THEN 'diverse' ELSE 'homogeneous'
        END AS bucket,
        COUNT(*) FILTER (WHERE payload->>'outcome' = 'promote') AS promoted,
        COUNT(*) FILTER (
            WHERE (payload->>'supersession_blocked')::boolean
        ) AS supersession_blocked,
        COUNT(*) AS eligible
    FROM events
    WHERE event_type = 'verified'
      AND object_type = 'fact'
      AND created_at >= :since
      AND created_at <= :until
      AND payload->'before'->>'verification_status' = 'candidate'
      AND (
            payload->>'outcome' IN ('promote', 'dispute')
            -- T2.60's blocked hold is a fact that MET its bar and did not
            -- promote, which is exactly what a promotion rate measures.
            -- Excluding it would let a widening block raise the reported
            -- rate by shrinking the denominator -- the silent inflation the
            -- T2.06 ruling minted the flag to prevent.
            OR (payload->>'outcome' = 'hold'
                AND (payload->>'supersession_blocked')::boolean)
          )
      AND (payload->>'origin_count')::int >= (payload->>'required_n')::int
    GROUP BY 1
    ORDER BY bucket
""")

# T2.06's exact false-promotion SQL (tests/test_ladder_journaling.py's
# _FALSE_PROMOTION_AUDIT_SQL), windowed on the corroboration side only. The
# dispute side is deliberately NOT bounded by `until`: a false promotion
# discovered after the audit window closes is still a false promotion, and
# clipping it would undercount the one number this metric may never
# undercount (doc 17 §5.1: "any false-promotion above bar vetoes loosening").
_FALSE_PROMOTION_AUDIT_SQL = text("""
    SELECT
        (
            SELECT COUNT(DISTINCT object_id) FROM events
            WHERE event_type = 'verified'
              AND object_type = 'fact'
              AND created_at >= :since AND created_at <= :until
              AND payload->'after'->>'verification_status' = 'corroborated'
        ) AS total_corroborations,
        (
            SELECT COUNT(DISTINCT p.object_id)
            FROM events p
            JOIN events d
              ON d.object_id = p.object_id
             AND d.event_type = 'verified'
             AND d.payload->>'outcome' = 'dispute'
             -- (created_at, id) tuple compare, not a bare created_at > --
             -- T2.06 found `now()` constant within one transaction, so a
             -- same-transaction dispute-after-corroboration pair needs the
             -- monotonic `id` to break the tie (doc/test precedent this
             -- module inherits verbatim).
             AND (d.created_at, d.id) > (p.created_at, p.id)
            WHERE p.event_type = 'verified'
              AND p.object_type = 'fact'
              AND p.created_at >= :since AND p.created_at <= :until
              AND p.payload->'after'->>'verification_status' = 'corroborated'
        ) AS disputed_after_corroboration
""")

# doc 17 §5.1's audit is a **distinct-fact union**, not a sum of the two
# arms. The overlap is the primary flow, not an edge case: the review queue
# serves the human disputed facts, so a fact they reject is in both arms by
# construction. Summing scored such a fact twice and reported a 200%
# false-promotion rate off a single fact.
_FALSE_PROMOTED_FACTS_SQL = text("""
    WITH corroborated AS (
        SELECT p.object_id, p.created_at, p.id
        FROM events p
        WHERE p.event_type = 'verified'
          AND p.object_type = 'fact'
          AND p.created_at >= :since AND p.created_at <= :until
          AND p.payload->'after'->>'verification_status' = 'corroborated'
    ),
    disputed_after AS (
        SELECT c.object_id
        FROM corroborated c
        JOIN events d
          ON d.object_id = c.object_id
         AND d.event_type = 'verified'
         AND d.object_type = 'fact'
         AND d.payload->'after'->>'verification_status' = 'disputed'
         AND (d.created_at, d.id) > (c.created_at, c.id)
    ),
    rejected_after AS (
        SELECT c.object_id
        FROM corroborated c
        JOIN events h
          ON h.object_id = c.object_id
         AND h.event_type = 'human_verdict'
         AND h.object_type = 'fact'
         AND h.payload->>'verdict' = 'rejected'
         AND (h.created_at, h.id) > (c.created_at, c.id)
    )
    SELECT COUNT(*) AS false_promoted_facts FROM (
        SELECT object_id FROM disputed_after
        UNION
        SELECT object_id FROM rejected_after
    ) u
""")





@dataclass(frozen=True)
class SliceResult:
    bucket: str
    promoted: int
    eligible: int
    # T2.60: how many of `eligible` met their bar and were withheld by the
    # supersession blocker. Reported beside the rate rather than folded into
    # it, because a low rate caused by blocking and a low rate caused by
    # starvation argue for opposite tuning moves (doc 17 §5.1's two-sided
    # evidence rule), and an aggregate cannot tell T2.40 which it is looking at.
    supersession_blocked: int = 0

    @property
    def rate(self) -> float | None:
        return self.promoted / self.eligible if self.eligible else None

    @property
    def powered(self) -> bool:
        return self.eligible >= UNDER_POWERED_THRESHOLD


@dataclass(frozen=True)
class FalsePromotionAudit:
    total_corroborations: int
    disputed_after_corroboration: int
    human_rejected: int
    #: DISTINCT facts satisfying *either* arm. Not derivable from the two
    #: counts above -- see `false_promotions`.
    false_promoted_facts: int = 0

    @property
    def false_promotions(self) -> int:
        """doc 17 §5.1's "**count of corroborated facts** later disputed
        **or** human-rejected" -- a distinct-fact union, not a sum.

        This was `disputed_after_corroboration + human_rejected` while the
        human-rejected arm was structurally 0, on a comment asserting the two
        sets could not overlap. **T2.63 made that false**, and the overlap is
        not exotic -- it is the primary flow: the review queue serves the
        human *disputed* facts, and the ones they reject are by construction
        in both arms. A single fact taken corroborated → disputed →
        human-rejected scored 2, reporting a 200% false-promotion rate off
        one fact.

        The error direction was conservative (it can falsely block G-C, never
        falsely clear it), but the bar quantity was wrong against its own
        definition, so it is counted as a union in SQL now.
        """
        return self.false_promoted_facts

    @property
    def rate(self) -> float | None:
        if not self.total_corroborations:
            return None
        return self.false_promotions / self.total_corroborations

    @property
    def powered(self) -> bool:
        return self.total_corroborations >= UNDER_POWERED_THRESHOLD


@dataclass(frozen=True)
class PromotionMetricsReport:
    since: datetime
    until: datetime
    database_identity: str
    schema_present: bool
    events_validated: int
    by_gate_fired: tuple[SliceResult, ...]
    by_diversity: tuple[SliceResult, ...]
    false_promotion: FalsePromotionAudit
    under_powered_threshold: int = UNDER_POWERED_THRESHOLD
    notes: tuple[str, ...] = field(default_factory=tuple)


async def _human_rejected_count(session: AsyncSession, *, since: datetime, until: datetime) -> int:
    """doc 17 §5.1's human-rejected half, read from the journal (T2.63).

    **This arm was structurally blind until T2.63 landed**, and the blindness
    was invisible: `review_state` was the only candidate source, T2.62 makes
    it pure queue membership ('open' or NULL, never a verdict), so the count
    read 0 forever while its own guard could never fire -- the vocabulary it
    watched was correct. A human verdict is an event, not a state, so the
    count now comes from `human_verdict` rows.

    The vocabulary check is retained but retargeted: `record_human_verdict`
    refuses an unknown verdict at the emitter, so an unrecognised value
    reaching this query means a second writer appeared that bypassed it.
    That is worth raising over rather than counting past.
    """
    verdicts = {
        row[0]
        for row in (
            await session.execute(_HUMAN_VERDICT_VOCABULARY_SQL, {"since": since, "until": until})
        ).all()
        if row[0] is not None
    }
    unknown = verdicts - KNOWN_HUMAN_VERDICTS
    if unknown:
        raise UnrecognisedPayloadError(
            f"human_verdict events carry unrecognised verdict(s) {sorted(unknown)} "
            f"-- record_human_verdict refuses anything outside "
            f"{sorted(KNOWN_HUMAN_VERDICTS)}, so a second writer has bypassed it. "
            f"The audit will not count past a verdict it cannot classify"
        )
    return int(
        (await session.execute(_HUMAN_REJECTED_SQL, {"since": since, "until": until})).scalar_one()
    )


async def compute_promotion_metrics(
    session: AsyncSession,
    *,
    since: datetime,
    until: datetime | None = None,
    database_identity: str = "unknown",
) -> PromotionMetricsReport:
    """The whole deliverable: validate, then measure, over `events` alone
    (plus the one permitted `knowledge_triples.review_state` read).

    Raises `UnrecognisedPayloadError` rather than returning a report if any
    `verified` payload or `review_state` value falls outside this module's
    known vocabulary -- that is the T2.60 guard, and it fires before any
    metric is computed so a bad number is never produced in the first place.
    """
    until = until or datetime.now(timezone.utc)

    events_validated = await validate_window(session, since=since)

    by_gate_rows = (
        await session.execute(_PROMOTION_RATE_BY_GATE_SQL, {"since": since, "until": until})
    ).all()
    by_gate = tuple(
        SliceResult(
            bucket=row.bucket, promoted=row.promoted, eligible=row.eligible,
            supersession_blocked=row.supersession_blocked,
        )
        for row in by_gate_rows
    )

    by_diversity_rows = (
        await session.execute(_PROMOTION_RATE_BY_DIVERSITY_SQL, {"since": since, "until": until})
    ).all()
    by_diversity = tuple(
        SliceResult(
            bucket=row.bucket, promoted=row.promoted, eligible=row.eligible,
            supersession_blocked=row.supersession_blocked,
        )
        for row in by_diversity_rows
    )

    audit_row = (
        await session.execute(_FALSE_PROMOTION_AUDIT_SQL, {"since": since, "until": until})
    ).one()
    human_rejected = await _human_rejected_count(session, since=since, until=until)
    false_promoted_facts = int(
        (await session.execute(_FALSE_PROMOTED_FACTS_SQL, {"since": since, "until": until}))
        .scalar_one()
    )
    false_promotion = FalsePromotionAudit(
        total_corroborations=audit_row.total_corroborations,
        disputed_after_corroboration=audit_row.disputed_after_corroboration,
        human_rejected=human_rejected,
        false_promoted_facts=false_promoted_facts,
    )

    notes: list[str] = []
    if not by_gate and not by_diversity:
        notes.append(
            "no eligible transitions in the window -- promotion rate is "
            "under-powered (0 observations), not a pass or a 0%"
        )
    if not false_promotion.total_corroborations:
        notes.append(
            "no corroborations in the window -- the false-promotion audit is "
            "under-powered (0 observations), not a pass or a 0%"
        )

    return PromotionMetricsReport(
        since=since,
        until=until,
        database_identity=database_identity,
        schema_present=True,
        events_validated=events_validated,
        by_gate_fired=by_gate,
        by_diversity=by_diversity,
        false_promotion=false_promotion,
        notes=tuple(notes),
    )


def no_schema_report(
    *, since: datetime, until: datetime, database_identity: str,
) -> PromotionMetricsReport:
    """The database has never been migrated -- no `events` table exists.

    Distinct from an empty-but-migrated journal: both are reported
    under-powered at 0 observations (the honest number either way), but this
    path is labelled so a reader does not mistake "never deployed" for
    "deployed and quiet".
    """
    empty_audit = FalsePromotionAudit(
        total_corroborations=0, disputed_after_corroboration=0, human_rejected=0,
    )
    return PromotionMetricsReport(
        since=since,
        until=until,
        database_identity=database_identity,
        schema_present=False,
        events_validated=0,
        by_gate_fired=(),
        by_diversity=(),
        false_promotion=empty_audit,
        notes=(
            "the target database has no `events` table (never migrated) -- "
            "treated as 0 observations by construction, under-powered, not a pass",
        ),
    )


def _render_slice_table(slices: tuple[SliceResult, ...]) -> str:
    """Renders `blocked` beside the rate, and that column is load-bearing.

    Widening the denominator to admit T2.60's blocked holds changed what
    `eligible` — and therefore every rate in this table — means. Without the
    blocked count on the **rendered** surface, a G-C reader cannot tell a low
    rate caused by blocking from one caused by starvation, and those two argue
    for opposite tuning moves (doc 17 §5.1's two-sided evidence rule). The
    in-memory dataclass carrying it is not enough: the report and the ledger
    row are what a gate run actually reads.
    """
    if not slices:
        return "| (no eligible transitions in window) | - | - | - | n/a **UNDER-POWERED** |\n"
    lines = []
    for s in slices:
        rate = f"{s.rate:.3f}" if s.rate is not None else "n/a"
        powered = "" if s.powered else " **UNDER-POWERED**"
        lines.append(
            f"| {s.bucket} | {s.promoted} | {s.supersession_blocked} | "
            f"{s.eligible} | {rate}{powered} |\n"
        )
    return "".join(lines)


def render_report(report: PromotionMetricsReport) -> str:
    fp = report.false_promotion
    fp_rate = f"{fp.rate:.4f}" if fp.rate is not None else "n/a"
    fp_powered = "" if fp.powered else " **UNDER-POWERED**"

    lines = [
        f"# Promotion metrics — {report.since.date().isoformat()} to "
        f"{report.until.date().isoformat()}\n",
        "\n",
        f"- database: `{report.database_identity}` (read-only)\n",
        f"- window: `{report.since.isoformat()}` .. `{report.until.isoformat()}`\n",
        f"- schema present: {report.schema_present}\n",
        f"- `verified` payloads validated (T2.60 / unknown-vocabulary guard): "
        f"{report.events_validated}\n",
        f"- under-powered threshold: < {report.under_powered_threshold} observations\n",
        "\n",
        "This is a measurement, not a verdict: no bar is stated or judged here "
        "(T2.40's role). Every rate below carries its denominator; a slice "
        "below the under-powered threshold is labelled, never read as a plain "
        "percentage.\n",
        "\n",
        "**Units: every promotion-rate figure below is per-transition "
        "(per journaled `verified` event), not per-fact.** Doc 17 §5.1 "
        "states the metric as `(facts promoted) / (eligible candidate "
        "facts)`; a fact that exits `candidate` more than once inside the "
        "window (e.g. promote, later demote, later re-promote) contributes "
        "one row per transition to both promoted and eligible here, not one "
        "row per fact. The false-promotion audit below is the one number in "
        "this report that IS de-duplicated to distinct facts (`COUNT(DISTINCT "
        "object_id)`), matching doc 17's own wording for that metric — do "
        "not read the two counting conventions as consistent with each "
        "other.\n",
        "\n",
        "## Promotion rate — by which N-fired gate (`gate_fired`)\n",
        "\n",
        "| gate_fired | promoted | blocked | eligible | rate |\n",
        "|---|---|---|---|---|\n",
        _render_slice_table(report.by_gate_fired),
        "\n",
        "## Promotion rate — by source-kind diversity\n",
        "\n",
        "**Caveat: the `diverse` bucket is not equivalent to \"the diversity "
        "gate fired\".** It buckets on whether the payload's `source_kinds` "
        "list (the union of kinds across every origin that ever asserted the "
        "fact, including a single origin whose own rows span two kinds) "
        "contains more than one distinct value. The ladder's actual "
        "diversity gate (`OriginProfile.kinds_are_diverse`) is stricter: it "
        "requires **two distinct, attributable origins** that differ in "
        "kind, and returns `False` outright for a lone origin regardless of "
        "how many kinds that one origin spans. So a fact asserted by exactly "
        "one origin under two kinds slices as `diverse` here without ever "
        "having lowered N — this is a deliberately independent cut (per doc "
        "17 §5.1's two-slice-axes instruction), not a proxy for `gate_fired "
        "= 'diversity'`; use the gate_fired table above for that question.\n",
        "\n",
        "| bucket | promoted | blocked | eligible | rate |\n",
        "|---|---|---|---|---|\n",
        _render_slice_table(report.by_diversity),
        "\n",
        "## False-promotion audit\n",
        "\n",
        "Count of DISTINCT corroborated facts later disputed or "
        "human-rejected (doc 17 §5.1). Sources: `events` self-join for the "
        "disputed half (T2.06's exact SQL, tuple-compared).\n",
        "\n",
        "**The human-rejected half is live as of T2.63.** It reads the "
        "`human_verdict` journal, not `review_state` -- that column is pure "
        "queue-membership (T2.62: only `open` is writable, cleared to NULL on "
        "resolution), so it could never carry a verdict and this count read 0 "
        "forever while its own tripwire could not fire. A 0 here is now a "
        "measurement, not an absence -- but note the only human verb reachable "
        "today is rejection; ratify is T2.05's and re-ground/edit have no owner, "
        "so this counts rejections rather than all adjudication.\n",
        "\n",
        f"- corroborations in window: {fp.total_corroborations}\n",
        f"- later disputed: {fp.disputed_after_corroboration}\n",
        f"- later human-rejected: {fp.human_rejected}\n",
        f"- DISTINCT facts in either arm: {fp.false_promotions}\n",
        f"- false-promotion rate: {fp_rate}{fp_powered}\n",
        "\n",
        "The three counts above do not sum: a fact the human rejects is "
        "usually one the queue served them *because* it was disputed, so it "
        "appears in both arms. doc 17 §5.1 counts facts, so the rate divides "
        "the DISTINCT union — summing the arms reported 200% off a single "
        "fact.\n",
    ]
    if report.notes:
        lines.append("\n## Notes\n\n")
        for note in report.notes:
            lines.append(f"- {note}\n")
        lines.append("\n")
    return "".join(lines)


def to_ledger_row(report: PromotionMetricsReport, *, extra: dict | None = None) -> dict:
    row = {
        "kind": "promotion_metrics_run",
        "since": report.since.isoformat(),
        "until": report.until.isoformat(),
        "database_identity": report.database_identity,
        "schema_present": report.schema_present,
        "events_validated": report.events_validated,
        "under_powered_threshold": report.under_powered_threshold,
        "by_gate_fired": [
            {
                "bucket": s.bucket, "promoted": s.promoted,
                # Load-bearing: the widened denominator changed what
                # `eligible` means, so a ledger row without this cannot
                # distinguish blocking from starvation after the fact.
                "supersession_blocked": s.supersession_blocked,
                "eligible": s.eligible,
                "rate": s.rate, "powered": s.powered,
            }
            for s in report.by_gate_fired
        ],
        "by_diversity": [
            {
                "bucket": s.bucket, "promoted": s.promoted,
                # Load-bearing: the widened denominator changed what
                # `eligible` means, so a ledger row without this cannot
                # distinguish blocking from starvation after the fact.
                "supersession_blocked": s.supersession_blocked,
                "eligible": s.eligible,
                "rate": s.rate, "powered": s.powered,
            }
            for s in report.by_diversity
        ],
        "false_promotion": {
            "total_corroborations": report.false_promotion.total_corroborations,
            "disputed_after_corroboration": report.false_promotion.disputed_after_corroboration,
            "human_rejected": report.false_promotion.human_rejected,
            # The headline the rate is derived from. Without it a ledger
            # reader sees the two arm counts beside a union-derived rate and
            # reconstructs the count by summing -- getting 2 where the
            # recorded rate says 1, which is precisely the arithmetic this
            # module was fixed to stop doing.
            "false_promotions": report.false_promotion.false_promotions,
            "rate": report.false_promotion.rate,
            "powered": report.false_promotion.powered,
        },
        "notes": list(report.notes),
    }
    if extra:
        row.update(extra)
    return row

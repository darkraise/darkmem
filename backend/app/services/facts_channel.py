"""The Layer-2 facts retrieval channel (doc 07 §2).

A channel, not a composition. This produces a ranked candidate list over one
epistemic layer with honest labels; merging it with the memory hybrid, applying
the verified-above-candidate ordering and grouping supporting memories under a
returned fact all belong to doc 07 §5's composition. Its shape follows the
memory hybrid's (``hybrid_search.py``), which §2 names the template every other
channel copies — including the honest-partial-results contract: a one-sided
failure degrades to the surviving arm, a both-sided failure raises rather than
returning an empty list nobody can tell from a genuine no-match.

**Born with pushdown (doc 07 §7).** ``project`` and the belief window are
rendered into the generating SQL, never re-applied in Python over a broad
fetch, so this channel cannot leak a foreign-project or window-closed row the
way a retrofit could — there is no Python filter step to leak past. ``project``
is a required argument for the same reason ``KnowledgeTripleRepository.get_live``
makes it one: an optional scope is a scope a caller can forget.

**The belief predicate is the currently-open-belief one, not "live".** Doc 08
§3.1 reserves "live" for ``expired_at IS NULL``, which still counts
window-closed rows as retained history. Serving those would present a
superseded belief as current, so the default channel scopes to
``OPEN_BELIEF_PREDICATE`` — the same predicate ``ux_knowledge_triples_open``
and the three retrieval indexes are partial on.

**Keyword-only, and it says so.** Doc 04 §5.3 ships the ``triple_embeddings``
template but defers its writer, so this channel has no semantic modality yet.
The trace therefore reports the semantic arm as present-and-not-run
(:meth:`FactChannelTrace.channel_status`) rather than omitting it: an absent
channel key is exactly the silent gap doc 07 §2 forbids, while ``ran=False``
is the report. It is never reported as *failed* — a deferred writer is not an
outage, and conflating them would make the envelope's ``partial`` flag lie.

**"Both sides" is not constructible from a query on this channel, and this
channel does not invent it.** Doc 08 §4.2 requires a disputed fact be served
labelled with both sides. The counterpart half — *disputed by fact X asserting
Y* — is computed inside ``contradiction_veto``, and the deterministic scan's
sole legitimate caller is the verification ladder, enforced by a tree-wide
reference scan that fails the build on a second entry point. So re-deriving it
from a retrieval surface is forbidden by construction, not merely awkward. What
ships here is the non-negotiable half: a disputed fact is **returned**, never
filtered out, labelled with everything its own row carries.

**T2.64 (2026-08-02) persisted the counterpart**, so the half this channel
leaves open is now available — but *not to a query on ``knowledge_triples``*.
It rides the ``verified`` event's payload as a ``contradiction`` block, which is
why the sentence above says "not constructible from a query on this channel"
rather than the original "not constructible today", which stopped being true.
Composing it onto a served row is T2.43's, reading the journal the way
``review_queue`` already does; :data:`DISPUTE_COUNTERPART_OWNER` names T2.64
because that is where the data comes from. A reader must not take the block's
absence for "no counterpart exists" — it is also absent on a recovery, on a
caller-overridden verdict, and on any dispute predating that commit.

**This channel records no retrieval heat (T2.65, 2026-08-04).** Every serve
here is invisible to doc 08 §6's consequence ranking, which reads only
``memory_access_stats`` (partially offset when the composed door's own
memory arm co-surfaces the fact's source memory — see ``review_ranking``'s
"Failure mode" paragraph). See :data:`RETRIEVAL_HEAT_STATUS` and
``review_ranking.FACT_KEYED_COUNTER_STATUS`` for the decision and its
reasoning — the short version is that a fact-keyed counter needs its own
table, and no lane holds baseline-schema clearance this round.
:data:`RETRIEVAL_HEAT_OWNER` names T2.84, the task that will build it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.knowledge_triples import OPEN_BELIEF_PREDICATE
from app.schemas.retrieval_trace import ChannelStatus
from app.services.rank_fusion import RankedList, rrf_fuse

logger = logging.getLogger(__name__)

__all__ = [
    "DISPUTE_COUNTERPART_OWNER",
    "FactChannelTrace",
    "FactsChannel",
    "KEYWORD_ARM",
    "LAYER",
    "NAME_ARM",
    "RETRIEVAL_HEAT_OWNER",
    "RETRIEVAL_HEAT_STATUS",
    "SEMANTIC_ARM",
    "SEMANTIC_ARM_OWNER",
]

LAYER = "L2"
ID_KIND = "fact"
DISPUTED = "disputed"

KEYWORD_ARM = "keyword"
NAME_ARM = "name"
SEMANTIC_ARM = "semantic"

# The task that ships the ``triple_embeddings`` writer, named as a value the way
# ``RankArm.activation`` names an arm's activation task, so a channel running
# without its semantic modality can never be mistaken for a channel that has one.
SEMANTIC_ARM_OWNER = "T2.33"

# The task that will make a dispute's counterpart readable. Carried on the
# label for the same reason.
DISPUTE_COUNTERPART_OWNER = "T2.64"

# T2.65 (2026-08-04): this channel feeds no retrieval-heat counter at all. A
# served fact never touches ``memory_access_stats`` (the frequency arm doc
# 08 §6's review ranking reads) the way the memory hybrid does through
# ``access_stats.spawn_record_access`` — there is no analogous call anywhere
# in ``search`` / ``search_with_trace``. This is measured, not assumed: this
# channel is the one ``layer_composition.LayerCompositionService.search``
# calls, which is itself wired live behind the ``knowledge_search`` MCP tool
# with no feature flag gating it, so every ``knowledge_search`` call already
# serves facts through exactly this uncounted path (partially offset when a
# query co-surfaces the fact's source memory through the composed door's own
# memory arm — see ``review_ranking``'s "Failure mode" paragraph for the
# bound). See ``review_ranking.FACT_KEYED_COUNTER_STATUS`` for the decision
# this forced and the reasoning behind it. Nothing reads this value back —
# it is a record, not a machine-checkable marker.
RETRIEVAL_HEAT_STATUS = "not recorded; see review_ranking.FACT_KEYED_COUNTER_STATUS (T2.65)"

# The task that will mint the fact-keyed counter this channel's serves
# currently feed nowhere. Named the same way ``SEMANTIC_ARM_OWNER`` and
# ``DISPUTE_COUNTERPART_OWNER`` above name theirs.
RETRIEVAL_HEAT_OWNER = "T2.84"

# The two arms split the channel's weight evenly, and the even split is a
# deliberate non-claim: no measurement says fact text outranks an endpoint name
# or the reverse. Promoting it to a config-row weight is the business of the
# tasks that own weights and their activation evidence, never an intuition
# edit here.
KEYWORD_ARM_WEIGHT = 0.5

# Each arm fetches this many times the requested limit. The memory hybrid
# carries the same multiplier for a different reason — absorbing the drop its
# semantic side takes when a predicate is applied post-scan (doc 07 §7) — and
# this channel has no drop at all, because both arms scope in SQL. The reason
# here is the fusion boundary: a fact sitting just past the cut in *both* arms
# accumulates more RRF mass than a fact leading only one, so fetching exactly
# the limit would lose it outright rather than merely reorder it.
ARM_FETCH_MULTIPLIER = 3

# Spelled to match ``ix_knowledge_triples_fact_fts`` and
# ``ix_knowledge_triples_name_fts`` verbatim — an expression index is matched
# textually, so a reformat here silently costs the index scan.
FACT_FTS = "to_tsvector('english', fact)"
NAME_FTS = "to_tsvector('simple', subject_name || ' ' || object_name)"

_FACT_QUERY = "plainto_tsquery('english', :q)"
_NAME_QUERY = "plainto_tsquery('simple', :q)"

_ROW_COLUMNS = """
    id, fact, subject_name, object_name, rel_type, project,
    verification_status, review_state, confidence, applies_when,
    demotion_pending_since,
    valid_at, invalid_at, expired_at, reference_time, created_at
"""


@dataclass(frozen=True)
class FactChannelTrace:
    """The channel's rows plus what each arm contributed before fusion.

    Built only by :meth:`FactsChannel.search_with_trace`, so a caller that does
    not want a trace never pays for the bookkeeping (doc 07 §8).
    """

    results: list[dict]
    arm_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    keyword_failed: bool = False
    name_failed: bool = False
    modalities: tuple[str, ...] = (KEYWORD_ARM, NAME_ARM)
    semantic_deferred_to: str = SEMANTIC_ARM_OWNER

    def channel_status(self) -> dict[str, ChannelStatus]:
        """This channel's contribution to doc 07 §8's ``channels`` envelope.

        The semantic entry is present and ``ran=False``. Dropping the key would
        make a channel that has no semantic modality indistinguishable from one
        whose composition never asked for it, which is the silent gap; marking
        it ``failed`` would put a deferred writer into the envelope's
        ``partial`` flag, which is a different lie.

        **These keys are unqualified and cannot be merged into
        ``RetrievalEnvelope.channels`` as they stand.** That dict is flat, and
        the memory hybrid already populates ``keyword`` and ``semantic`` in it,
        so a naive merge overwrites the memory channel's entries and a memory
        keyword outage disappears from the envelope's ``partial`` flag. Nothing
        consumes this method yet; whoever composes the four layers owns the
        namespacing, and merging before deciding it loses status silently.
        """
        return {
            KEYWORD_ARM: ChannelStatus(ran=True, failed=self.keyword_failed),
            NAME_ARM: ChannelStatus(ran=True, failed=self.name_failed),
            SEMANTIC_ARM: ChannelStatus(ran=False),
        }


class FactsChannel:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self,
        query: str,
        *,
        project: str,
        limit: int = 20,
        keyword_weight: float = KEYWORD_ARM_WEIGHT,
    ) -> list[dict]:
        keyword_rows, name_rows, _, _ = await self._run_arms(query, project, limit)
        return self._fuse(keyword_rows, name_rows, keyword_weight, limit)

    async def search_with_trace(
        self,
        query: str,
        *,
        project: str,
        limit: int = 20,
        keyword_weight: float = KEYWORD_ARM_WEIGHT,
    ) -> FactChannelTrace:
        keyword_rows, name_rows, keyword_failed, name_failed = await self._run_arms(
            query, project, limit,
        )

        arm_scores: dict[str, dict[str, float]] = {}
        for arm, rows in ((KEYWORD_ARM, keyword_rows), (NAME_ARM, name_rows)):
            for row in rows:
                arm_scores.setdefault(row["fact_id"], {})[arm] = float(row["score"])

        return FactChannelTrace(
            results=self._fuse(keyword_rows, name_rows, keyword_weight, limit),
            arm_scores=arm_scores,
            keyword_failed=keyword_failed,
            name_failed=name_failed,
        )

    async def _run_arms(
        self, query: str, project: str, limit: int,
    ) -> tuple[list[dict], list[dict], bool, bool]:
        fetch_n = limit * ARM_FETCH_MULTIPLIER
        keyword_failed = False
        name_failed = False

        # Each arm runs inside its own SAVEPOINT. Both share one session, and a
        # database-level error aborts the entire transaction, so without one
        # the surviving arm's own valid SQL fails on the aborted transaction: a
        # one-sided outage reports as a both-sided one, naming an arm that never
        # independently failed, and the caller's session is poisoned for
        # everything it does after the search. The memory hybrid carries the
        # same idiom (``hybrid_search._run_channels``) and they change together.
        try:
            async with self.session.begin_nested():
                keyword_rows = await self._run(
                    self.keyword_query(query, project, fetch_n), KEYWORD_ARM,
                )
        except Exception as e:
            logger.error("Facts keyword arm failed: %s", e)
            keyword_rows = []
            keyword_failed = True

        try:
            async with self.session.begin_nested():
                name_rows = await self._run(
                    self.name_query(query, project, fetch_n), NAME_ARM,
                )
        except Exception as e:
            logger.error("Facts name arm failed: %s", e)
            name_rows = []
            name_failed = True

        # One arm down degrades to the other; both down means an empty list
        # would be indistinguishable from a genuine no-match, so the outage is
        # raised rather than served as an answer (doc 07 §2, invariant 14).
        if keyword_failed and name_failed:
            raise RuntimeError("Facts channel failed on both the keyword and name arms")

        return keyword_rows, name_rows, keyword_failed, name_failed

    def keyword_query(self, query: str, project: str, limit: int) -> tuple[str, dict]:
        """The fact-text FTS statement and its bound parameters.

        Exposed so the query plan and the pushed-down predicates can be
        measured against the statement the channel actually runs, rather than
        against a transcription of it.
        """
        sql = f"""
                SELECT {_ROW_COLUMNS},
                       ts_rank({FACT_FTS}, {_FACT_QUERY}) AS score
                FROM knowledge_triples
                WHERE {FACT_FTS} @@ {_FACT_QUERY}
                  AND project = CAST(:project AS text)
                  AND {OPEN_BELIEF_PREDICATE}
                ORDER BY score DESC, created_at, id
                LIMIT CAST(:limit AS integer)
        """
        return sql, {"q": query, "project": project, "limit": limit}

    def name_query(self, query: str, project: str, limit: int) -> tuple[str, dict]:
        """The subject/object name-match statement and its bound parameters."""
        sql = f"""
                SELECT {_ROW_COLUMNS},
                       ts_rank({NAME_FTS}, {_NAME_QUERY}) AS score
                FROM knowledge_triples
                WHERE {NAME_FTS} @@ {_NAME_QUERY}
                  AND project = CAST(:project AS text)
                  AND {OPEN_BELIEF_PREDICATE}
                ORDER BY score DESC, created_at, id
                LIMIT CAST(:limit AS integer)
        """
        return sql, {"q": query, "project": project, "limit": limit}

    async def _run(self, statement: tuple[str, dict], arm: str) -> list[dict]:
        sql, params = statement
        result = await self.session.execute(text(sql), params)
        return [_row_to_candidate(row, arm) for row in result.mappings().all()]

    @staticmethod
    def _fuse(
        keyword_rows: list[dict],
        name_rows: list[dict],
        keyword_weight: float,
        limit: int,
    ) -> list[dict]:
        """This channel's two ranked lists, joined under their list weights.

        Intra-channel only. The fused rows are candidates for doc 07 §5's
        composition, not a result set: nothing here ranks a fact against a
        memory or an article.
        """
        return rrf_fuse(
            [
                RankedList(KEYWORD_ARM, keyword_rows, keyword_weight),
                RankedList(NAME_ARM, name_rows, 1.0 - keyword_weight),
            ],
            limit,
        )


def _dispute_label(row) -> dict | None:
    """The dispute half of the row's labels, or ``None`` when undisputed.

    ``counterpart`` is structurally ``None``: the contradiction finding that
    knows the competing claim is computed inside adjudication and never
    persisted, and this surface may not re-derive it. Emitting the key with a
    named owner is the honest shape — a consumer can tell "no counterpart is
    knowable yet" from "this fact has no counterpart", which dropping the key
    would collapse.
    """
    if row["verification_status"] != DISPUTED:
        return None
    return {
        "review_state": row["review_state"],
        "counterpart": None,
        "counterpart_owner": DISPUTE_COUNTERPART_OWNER,
    }


def _row_to_candidate(row, arm: str) -> dict:
    fact_id = str(row["id"])
    return {
        # One id, two spellings, written from one expression. ``fact_id`` is
        # doc 07 §5's key for the fact object space; ``id`` is what
        # ``rank_fusion.normalize_row_id`` reads, and a row it cannot key is a
        # row the shared fusion drops without a word.
        "fact_id": fact_id,
        "id": fact_id,
        "id_kind": ID_KIND,
        "layer": LAYER,
        "score": float(row["score"]),
        "source": arm,
        "fact": row["fact"],
        "subject_name": row["subject_name"],
        "object_name": row["object_name"],
        "rel_type": row["rel_type"],
        "project": row["project"],
        "verification_status": row["verification_status"],
        "review_state": row["review_state"],
        "confidence": row["confidence"],
        "applies_when": row["applies_when"],
        # The ``under-sourced`` overlay (doc 08 §4.3) rides the row for the
        # same reason ``review_state`` does: a corroborated fact one lost
        # source from demotion is not the same claim as a healthy one, and a
        # consumer that cannot see the difference presents it as one.
        "demotion_pending_since": row["demotion_pending_since"],
        # ``invalid_at`` and ``expired_at`` are NULL on every row this channel
        # can return, by its own predicate — and carrying them anyway is what
        # makes that observable. A non-NULL one reaching a consumer is the
        # scope failing, which a dropped label would hide.
        "belief_window": {
            "valid_at": row["valid_at"],
            "invalid_at": row["invalid_at"],
            "expired_at": row["expired_at"],
            "reference_time": row["reference_time"],
        },
        "created_at": row["created_at"],
        "dispute": _dispute_label(row),
    }

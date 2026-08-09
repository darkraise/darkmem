"""The citation re-verifier — doc 10 §6's second sanctioned crossing.

A code citation records an *address*: ``detail = {commit_sha, basis, file_path,
symbol_key}``, where ``symbol_key`` is an owner-qualified ``code_graph_nodes``
key and never a bigint node id, which the indexer churns on every full re-index
(invariant 9). An address recorded at one HEAD can stop resolving at the next.
When it does, this module marks the ``fact_sources`` row stale, journals *why*,
and enqueues the citing fact for the Tier-C verification recompute — which is
what actually moves the badge.

**It never expires anything, and that is the design's point, not an omission.**
A symbol that vanished may be a rename a human should confirm rather than a
retraction of the claim, so the outcome is label-and-queue. Nothing here writes
``expired_at``, ``invalid_at`` or ``verification_status``; a source scan in
``tests/test_citation_reverifier.py`` fails the build if it ever does.

**The downgrade is a demotion of corroboration, never ``disputed``.** A lost
source is not a contradiction. This module states no target status at all — it
changes the *evidence*, and the Tier-C verification recompute — the sole
journaller of verification transitions — decides the rung from it. (Named by
role rather than by symbol: ``tests/test_verification_ladder.py`` scans every
line under ``app/`` for that function's name, docstrings included, because a
module that can spell it is one edit away from calling it.) That indirection is
what
keeps the journal a true description of the vault, and it only works because a
stale row genuinely stops counting: ``LIVE_SOURCE_PREDICATE``
(``repositories/fact_sources.py``) is where the marker acquires its arithmetic.
Without that predicate this whole module would be decoration that passes its own
tests.

**Reading the code graph, writing the vault, in two statements — never one.**
The never-join rule forbids a statement that reads a ``code_graph_nodes`` row
and a ``fact_sources`` / ``knowledge_triples`` row together. So the crossing is
carried by *parameters*: ``_repo_heads`` and ``_resolve_keys`` name only
code-side tables, ``_CANDIDATES`` and the writes name only vault tables, and the
shas and keys travel between them through Python. Nothing here can degrade into
a join by someone "simplifying" a query, because the two halves have no table in
common to join on.

**How a run's changed-file set crosses into a job that runs later, and why this
design does not need it to.** ``CodePipeline`` holds ``_changed_files`` /
``_deleted_files`` in memory for the duration of the run; a Tier-C job in a
later session cannot see them. Doc 10 §6 scopes the walk to that set as the cost
bound. This module scopes on a different axis that is *durable by construction*:
a citation is re-resolved when the sha it was last verified at is not the
repository's current ``last_indexed_commit``. Three properties follow.

- It is **self-healing**. The scope is derived from two stored columns, not from
  a delivered message. Persisting the changed set instead — through an event
  payload, the local precedent being ``index_debt``'s ``repo_indexed`` journal —
  would make the walk depend on ``record_event``, which by contract degrades
  loudly and never raises; a swallowed emit would strand that run's citations
  forever with nothing able to notice, and the backstop that healed it would
  have to be exactly this sha comparison. So the file-scoped design needs this
  one underneath it, while this one needs nothing underneath it.
- It **subsumes runs**. Two re-index runs landing between two ticks leave one
  HEAD, and re-resolution is always against the graph as it stands now, so the
  intermediate run's file set is not merely lost but irrelevant — a citation
  broken by run A and restored by run B resolves, correctly, once.
- It **costs more than the file scoping**, and this is the honest trade: an
  unchanged file's citation is re-resolved once per HEAD move rather than never.
  The bound is the repository's own citation count (doc 10 §6 sizes a repo at
  10–200 facts), so a tick is tens to hundreds of indexed key lookups plus one
  small jsonb write each, not a function of repository size. Layering the file
  scoping on top later is a pure optimisation of this predicate, not a change to
  what it decides.

**Idempotency comes from the same stamp.** ``detail.reverified_at_sha`` records
the HEAD each row was last resolved against — ``detail.commit_sha`` cannot serve,
because ``add_source`` is first-assertion-wins and it stays at the sha the
citation was *born* at forever. A second tick over an unmoved HEAD selects no
candidates, so it marks nothing, journals nothing and enqueues nothing. That is
also the provenance no-op: a run whose files changed but whose citations all
still resolve stamps the new sha and emits **no** event, because an event there
is indistinguishable to the drain from real evidence movement and would thrash
``corroborated <-> candidate`` on facts whose evidence never moved.

**A citation with no ``symbol_key`` is an input, not an edge case.** The lift
logs one at mint time when no witness could be found for an asserted name, and
such a row has no address to re-resolve. It is counted (``keyless`` on the
outcome) and reported in the tick's log line rather than skipped in silence, and
it is **never** marked stale: "cannot be checked" is not "checked and broken",
and marking it would demote a badge on the strength of missing bookkeeping.

**Recovery is symmetric.** A key that resolves again — the rename undone, the
file restored — clears the marker and emits ``sources_changed``, so the fact
climbs back by the same recompute that demoted it. Only *expiry* is reserved for
the human; a badge is evidence-driven in both directions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fact_sources import CODE_SOURCE_KIND, STALE_DETAIL_KEY
from app.services.events import CITATION_STALE, record_event
from app.services.job_registry import FieldDescriptor

logger = logging.getLogger(__name__)

CITATION_REVERIFY_JOB_KEY = "citation_reverify"

# Hourly, at :45. The three sibling code/graph Tier-C jobs already sit at :15
# (relation embeddings) and :30 (the PPR snapshot); a fourth on the hour would
# stack four scans on one minute for no reason. Ordering against the lift is
# deliberately *not* expressed here: neither job depends on the other's output,
# and a re-verifier that only worked when it ran second would be a scheduling
# constraint disguised as a correctness one.
CITATION_REVERIFY_CRON = "45 * * * *"
CITATION_REVERIFY_MIN_INTERVAL_SECONDS = 300
CITATION_REVERIFY_MAX_RUN_SECONDS = 600

DEFAULT_REVERIFY_BATCH = 500
MAX_REVERIFY_BATCH = 5000

CITATION_REVERIFY_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="batch_size",
        label="Batch Size",
        default=DEFAULT_REVERIFY_BATCH,
        min=1,
        max=MAX_REVERIFY_BATCH,
        help=(
            "Code citations re-resolved per run. A citation enters the batch "
            "once per HEAD move of its repository, so this bounds a burst "
            "after a large re-index; whatever it leaves behind is picked up by "
            "the next run, because the sha stamp that selects it is durable."
        ),
    ),
]

# The sha a row was last resolved against. Its own key rather than a rewrite of
# `commit_sha`, which is the sha the citation was *born* at and is what a human
# reads to know when the claim was made -- overwriting it would destroy that and
# make the two questions ("asserted when?" / "checked when?") one answer.
REVERIFIED_AT_SHA_KEY = "reverified_at_sha"

# The sha at which the address stopped resolving, which doc 10 §6 requires the
# marker carry. Kept beside the marker and cleared with it, so a row can never
# read "stale, at no particular commit".
STALE_AT_SHA_KEY = "stale_at_sha"


# ── the code side: two statements that name no vault table ──


_REPO_HEADS = text(
    "SELECT CAST(id AS text) AS repo_id, last_indexed_commit "
    "FROM repositories WHERE last_indexed_commit IS NOT NULL"
)

_RESOLVE_KEYS = text("""
    SELECT DISTINCT key
    FROM code_graph_nodes
    WHERE repo_id = CAST(:rid AS uuid)
      AND key = ANY(CAST(:keys AS text[]))
""")


async def _repo_heads(session: AsyncSession) -> dict[str, str]:
    rows = (await session.execute(_REPO_HEADS)).mappings().all()
    return {row["repo_id"]: row["last_indexed_commit"] for row in rows}


async def _resolve_keys(
    session: AsyncSession, *, repo_id: str, keys: list[str]
) -> set[str]:
    """Which of ``keys`` still name a node in this repository's graph.

    **Node kind is deliberately unconstrained.** A citation's ``basis`` implies
    one (an import addresses a ``module``, a language addresses a ``file``), and
    a future producer citing a symbol would address a ``symbol``; matching on
    the key alone accepts a key that resolves under an unexpected kind. That
    errs toward "still resolves", which under-claims — the direction this whole
    subsystem's errors are required to take — where a kind filter that drifted
    from a producer's spelling would manufacture staleness and demote badges on
    working citations.
    """
    if not keys:
        return set()
    result = await session.execute(_RESOLVE_KEYS, {"rid": repo_id, "keys": keys})
    return {row[0] for row in result.all()}


# ── the vault side: statements that name no code table ──


# `unnest` of two parallel arrays rather than a join to `repositories`: the
# repository heads arrive as parameters, already read by the code-side statement
# above, so this is the crossing carried by application code that doc 10 §6
# sanctions rather than the graph join doc 01 §3.6 forbids. Both arrays are CAST
# because asyncpg cannot infer a bare array parameter's type through `unnest`.
#
# `COALESCE(reverified_at_sha, commit_sha)` is what makes a citation minted at
# the current HEAD cost nothing on its first tick: it was resolved by the lift a
# moment ago against the graph it is being compared to.
_CANDIDATES = text(f"""
    SELECT fs.id AS source_id, fs.fact_id, fs.source_ref AS repo_ref,
           fs.detail, kt.project, head.sha AS head_sha
    FROM fact_sources fs
    JOIN knowledge_triples kt ON kt.id = fs.fact_id
    JOIN unnest(CAST(:repo_ids AS text[]), CAST(:shas AS text[]))
         AS head(repo_id, sha) ON head.repo_id = fs.source_ref
    WHERE fs.source_kind = CAST(:kind AS text)
      AND COALESCE(
              fs.detail ->> '{REVERIFIED_AT_SHA_KEY}',
              fs.detail ->> 'commit_sha'
          ) IS DISTINCT FROM head.sha
    ORDER BY fs.source_ref, fs.fact_id, fs.id
    LIMIT CAST(:batch AS integer)
""")

# One statement for every outcome, because every outcome is the same write: the
# whole `detail` object, rebuilt in Python and cast back. Merging with `||` in
# SQL would need a second statement for the clear (jsonb has no conditional key
# removal) and the two would drift.
_WRITE_DETAIL = text(
    "UPDATE fact_sources SET detail = CAST(:detail AS jsonb) "
    "WHERE id = CAST(:id AS uuid)"
)


@dataclass(frozen=True)
class ReverifyOutcome:
    """What one tick did, for the job log and for the tests.

    ``marked`` and ``cleared`` are the only two that journal; ``confirmed`` and
    ``keyless`` are the no-op halves and are counted precisely so a tick that
    did nothing can be told apart from a tick that found nothing to do.
    """

    citations_scanned: int = 0
    marked_stale: int = 0
    cleared: int = 0
    confirmed: int = 0
    already_stale: int = 0
    keyless: int = 0
    facts_enqueued: int = 0


def _detail_of(raw: object) -> dict:
    """A citation's ``detail`` as a dict, whatever the column actually holds.

    Nullable and free-form on disk: a row written before the four-key shape
    settled, or by a caller that passed no detail at all, must not take a tick
    down. An unreadable detail degrades to an empty one, which has no
    ``symbol_key`` and therefore lands on the keyless path — counted and
    reported, never marked stale.
    """
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _is_stale(detail: dict) -> bool:
    return detail.get(STALE_DETAIL_KEY) is True


async def _enqueue(
    session: AsyncSession, *, fact_id: UUID, repo_ref: str, project: str | None
) -> None:
    """The evidence-moved signal the Tier-C recompute drains.

    The same event type and the same payload spelling the lift and the
    withdrawal sweep already emit, deliberately: the drain dedups by
    ``payload.fact_id``, so a third spelling of one fact's evidence movement
    would split it into two units of work rather than one.
    """
    await record_event(
        session,
        event_type="sources_changed",
        object_type="fact",
        object_id=fact_id,
        project=project,
        payload={"fact_id": str(fact_id), "repo_id": repo_ref},
    )


async def _journal_stale(
    session: AsyncSession,
    *,
    fact_id: UUID,
    repo_ref: str,
    project: str | None,
    detail: dict,
    head_sha: str,
) -> None:
    """Doc 10 §6's re-verify outcome, on the journal.

    Carries the address and the two shas and nothing else. The payload
    deliberately copies **no** fact text and no source content: a journal row
    outlives the deletion of its subject, the standing rule is write-time
    minimisation, and an address plus the commit it broke at is the whole of
    what a human needs to go look at the rename that caused it.
    """
    await record_event(
        session,
        event_type=CITATION_STALE,
        object_type="fact",
        object_id=fact_id,
        project=project,
        payload={
            "fact_id": str(fact_id),
            "repo_id": repo_ref,
            "symbol_key": detail.get("symbol_key"),
            "basis": detail.get("basis"),
            "minted_at_sha": detail.get("commit_sha"),
            "broken_at_sha": head_sha,
        },
    )


async def reverify_citations(
    session: AsyncSession, *, batch_size: int = DEFAULT_REVERIFY_BATCH
) -> ReverifyOutcome:
    """One re-verification tick. Does not commit — the caller owns the
    transaction, matching every other Tier-C entry point.

    The repository heads are read once for the whole tick rather than per
    citation: a repo asserts tens to hundreds of facts and they all compare
    against the same sha.
    """
    heads = await _repo_heads(session)
    if not heads:
        return ReverifyOutcome()

    repo_ids = list(heads)
    rows = (
        await session.execute(
            _CANDIDATES,
            {
                "repo_ids": repo_ids,
                "shas": [heads[repo_id] for repo_id in repo_ids],
                "kind": CODE_SOURCE_KIND,
                "batch": batch_size,
            },
        )
    ).mappings().all()
    if not rows:
        return ReverifyOutcome()

    candidates = [
        (dict(row), _detail_of(row["detail"])) for row in rows
    ]

    # Resolved once per repository over that repository's whole key set, so a
    # repo asserting 200 citations costs one lookup rather than 200.
    keys_by_repo: dict[str, set[str]] = {}
    for row, detail in candidates:
        key = detail.get("symbol_key")
        if isinstance(key, str) and key:
            keys_by_repo.setdefault(str(row["repo_ref"]), set()).add(key)
    resolved: dict[str, set[str]] = {
        repo_ref: await _resolve_keys(session, repo_id=repo_ref, keys=sorted(keys))
        for repo_ref, keys in keys_by_repo.items()
    }

    marked = cleared = confirmed = already_stale = keyless = 0
    enqueued: set[str] = set()
    for row, detail in candidates:
        repo_ref = str(row["repo_ref"])
        head_sha = row["head_sha"]
        fact_id = UUID(str(row["fact_id"]))
        key = detail.get("symbol_key")
        has_key = isinstance(key, str) and bool(key)
        still_resolves = has_key and key in resolved.get(repo_ref, set())
        was_stale = _is_stale(detail)

        updated = dict(detail)
        updated[REVERIFIED_AT_SHA_KEY] = head_sha

        if not has_key:
            # No address, so nothing was checked. The stamp still advances: a
            # row that can never be re-verified must not be re-selected on
            # every tick forever, and its unverifiability is reported through
            # the outcome rather than through repeated work.
            keyless += 1
        elif still_resolves and was_stale:
            updated.pop(STALE_DETAIL_KEY, None)
            updated.pop(STALE_AT_SHA_KEY, None)
            cleared += 1
        elif still_resolves:
            confirmed += 1
        elif was_stale:
            # Already labelled at an earlier sha, and `stale_at_sha` keeps that
            # earlier one: the citation broke once, and re-observing it broken
            # is not a second break. This is the branch that makes a second tick
            # over the same repository run produce one marking and one event.
            already_stale += 1
        else:
            updated[STALE_DETAIL_KEY] = True
            updated[STALE_AT_SHA_KEY] = head_sha
            marked += 1

        await session.execute(
            _WRITE_DETAIL,
            {"id": str(row["source_id"]), "detail": json.dumps(updated)},
        )

        if updated.get(STALE_DETAIL_KEY) is True and not was_stale:
            await _journal_stale(
                session,
                fact_id=fact_id,
                repo_ref=repo_ref,
                project=row["project"],
                detail=updated,
                head_sha=head_sha,
            )
        if _is_stale(updated) != was_stale:
            await _enqueue(
                session, fact_id=fact_id, repo_ref=repo_ref, project=row["project"]
            )
            enqueued.add(str(fact_id))

    outcome = ReverifyOutcome(
        citations_scanned=len(candidates),
        marked_stale=marked,
        cleared=cleared,
        confirmed=confirmed,
        already_stale=already_stale,
        keyless=keyless,
        facts_enqueued=len(enqueued),
    )
    if outcome.keyless:
        logger.warning(
            "citation re-verify: %d of %d citations carry no symbol_key and "
            "cannot be re-verified; their badges rest on evidence nothing can "
            "check against a new HEAD",
            outcome.keyless, outcome.citations_scanned,
        )
    if outcome.marked_stale or outcome.cleared:
        logger.info(
            "citation re-verify: %d scanned, %d marked stale, %d cleared, "
            "%d still resolving, %d facts enqueued",
            outcome.citations_scanned, outcome.marked_stale, outcome.cleared,
            outcome.confirmed, outcome.facts_enqueued,
        )
    return outcome

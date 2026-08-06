"""The cached PPR snapshot the graph arms rank against (doc 07 §4).

The entity graph is built on every ingest and, until this module, never spent
on retrieval. Spending it means one thing: personalized PageRank seeded from a
query's entities, its mass projected onto memories, fused into RRF **as a
ranked list** rather than added as a raw magnitude — so PPR lives in the same
scale-free currency as every other producer and the brittle per-modality
min-max normalisation never appears (doc 07 §3).

**The snapshot is built off the hot path and never per query.** A per-query
graph build would put the whole project's entity graph on the query's latency
budget; the Tier-C job below rebuilds it on a cron and retrieval reads whatever
is in the cache. A missing snapshot is not an error — it is a project the job
has not reached yet, and the arm contributes nothing for it.

**Invariant 13, stated where an implementer meets it.** This cache lives in one
process and is correct *because* there is exactly one uvicorn worker. Under
multiple replicas each would serve a different snapshot of the same project,
and two identical queries would rank differently depending on which replica
answered — with no error and no symptom. Closing that needs sticky routing or a
serialised snapshot table, and it is a flagged Phase-4 decision (doc 02 §11),
deliberately not solved here.

**Invariant 15 holds by construction, not by discipline.** The PPR arm reads
the cached snapshot and nothing else: the seed set is derived from the
snapshot's own in-process entity→memory mapping, so an active arm adds no
query-time database read and no model call. Nothing on the retrieval path can
trigger a rebuild.

**Nodes are entities, not memories, and that is not interchangeable with the
topic projection.** `memory_projection` clusters memories because
`memory_community_members` keys on `memory_id`. PPR seeds from the entities a
query resolves to and needs mass to flow *along relations*, which only exist
between entities. The two graphs answer different questions over the same rows
and neither can be derived from the other by relabelling.

**Synonymy edges live inside the snapshot and are never `entity_relations`
rows** (doc 04 §4.2, doc 06 §6). Two entities the extractor kept apart but
whose embeddings sit within `synonymy_threshold` should let mass flow between
them; writing that as a graph row would assert a relationship the extractor
never found and would then be indistinguishable from one it did.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.embedder_registry import child_table
from app.services.job_registry import FieldDescriptor

logger = logging.getLogger(__name__)

PPR_SNAPSHOT_JOB_KEY = "ppr_snapshot"

DEFAULT_DAMPING = 0.85
DEFAULT_SYNONYMY_THRESHOLD = 0.8
DEFAULT_SYNONYMY_TOP_K = 5

# Above this node count the synonymy arm is skipped rather than run. Exact KNN
# inside a project cannot ride the global ANN index without post-filtering, so
# it is quadratic in the project's entity count; a project past this bound gets
# a relation-only snapshot that records `synonymy_skipped` rather than a
# silently thinner graph.
DEFAULT_SYNONYMY_MAX_NODES = 2_000

DEFAULT_MAX_SNAPSHOT_EDGES = 2_000_000
DEFAULT_PROJECT_BATCH = 5
DEFAULT_BUILD_TIMEOUT_SECONDS = 60.0

SKIPPED_LIBRARY_UNAVAILABLE = "library_unavailable"
SKIPPED_TOO_MANY_EDGES = "max_snapshot_edges"
SKIPPED_NO_NODES = "no_nodes"

DEGRADED_SYNONYMY_SKIPPED = "synonymy_skipped"

PPR_SNAPSHOT_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="batch_size", label="Projects Per Run",
        default=DEFAULT_PROJECT_BATCH, min=1, max=100,
        help="Projects whose snapshot is rebuilt per run, in rotating order.",
    ),
    # Percent rather than the 0.8 cosine doc 07 §4 states, because
    # `FieldDescriptor.default` is typed `int`: the whole per-job config
    # surface — schema, validation and the generic UI renderer — is integer.
    # Widening that type for one field would change a contract five other jobs
    # share; 80 expresses 0.8 exactly and the runner divides.
    FieldDescriptor(
        key="synonymy_threshold_pct", label="Synonymy Threshold (%)",
        default=int(DEFAULT_SYNONYMY_THRESHOLD * 100), min=0, max=100,
        help=(
            "Cosine similarity, in percent, at or above which two entities get "
            "a synonymy edge inside the snapshot. Never entity_relations rows."
        ),
    ),
    FieldDescriptor(
        key="synonymy_top_k", label="Synonymy Neighbours",
        default=DEFAULT_SYNONYMY_TOP_K, min=0, max=50,
        help="Nearest neighbours considered per entity; 0 disables the arm.",
    ),
    FieldDescriptor(
        key="synonymy_max_nodes", label="Synonymy Node Ceiling",
        default=DEFAULT_SYNONYMY_MAX_NODES, min=0, max=1_000_000,
        help=(
            "Projects with more entities than this get a relation-only "
            "snapshot; the exact within-project KNN is quadratic."
        ),
    ),
    FieldDescriptor(
        key="max_snapshot_edges", label="Maximum Snapshot Edges",
        default=DEFAULT_MAX_SNAPSHOT_EDGES, min=1_000, max=100_000_000,
        help="A graph wider than this is skipped loudly rather than truncated.",
    ),
    FieldDescriptor(
        key="build_timeout_seconds", label="Build Timeout (s)",
        default=int(DEFAULT_BUILD_TIMEOUT_SECONDS), min=1, max=600,
        help="Past this the project keeps its previous snapshot, if any.",
    ),
]


# ── the SQL ──────────────────────────────────────────────────────────
#
# `AS MATERIALIZED` for the reason the buffer-claim CTE records in CLAUDE.md:
# a plain sub-select lets the planner re-execute it per outer row, which here
# means re-deriving the project's whole eligible set for every relation.
#
# Eligibility is spelled exactly as `ix_memories_project_live`'s predicate
# spells it, plus the `expires_at` clause `memory_projection` documents: the
# sweep is periodic, so an expired-but-unswept row is still `status='active'`
# and must not carry mass.

_ELIGIBLE_AND_NODES = """
WITH eligible AS MATERIALIZED (
    SELECT id
    FROM memories
    WHERE project = CAST(:project AS text)
      AND status = 'active'
      AND is_archived = false
      AND (expires_at IS NULL OR expires_at > now())
),
nodes AS MATERIALIZED (
    SELECT e.id AS entity_id, array_agg(DISTINCT el.id) AS memory_ids
    FROM entities e
    JOIN LATERAL unnest(e.memory_ids) AS u(mid) ON TRUE
    JOIN eligible el ON el.id = u.mid
    GROUP BY e.id
)
"""

_NODES_SQL = text(_ELIGIBLE_AND_NODES + """
SELECT entity_id, memory_ids FROM nodes ORDER BY entity_id
""")

# Weight is the number of relation rows joining the pair. `entity_relations` is
# unique on (source, target, rel_type), so a pair asserted through several
# relation types is more strongly connected than one asserted through a single
# type — and counting rows says that without inventing a magnitude.
_RELATION_EDGES_SQL = text(_ELIGIBLE_AND_NODES + """
SELECT r.source_entity_id AS src, r.target_entity_id AS tgt,
       count(*)::float8 AS weight
FROM entity_relations r
JOIN nodes s ON s.entity_id = r.source_entity_id
JOIN nodes t ON t.entity_id = r.target_entity_id
WHERE r.source_entity_id <> r.target_entity_id
GROUP BY r.source_entity_id, r.target_entity_id
""")


def _synonymy_sql(table: str) -> "text":
    """The within-project KNN, against one fingerprint's child table.

    Interpolating the table name is how every partition consumer reaches a
    child table; the name comes from `child_table`, never from a caller
    (invariant: no cross-fingerprint join — one fingerprint, one query).
    """
    return text(_ELIGIBLE_AND_NODES + f"""
, vecs AS MATERIALIZED (
    SELECT ee.entity_id, ee.embedding
    FROM {table} ee
    JOIN nodes n ON n.entity_id = ee.entity_id
    WHERE ee.fingerprint = CAST(:fingerprint AS text)
)
SELECT v.entity_id AS src, k.entity_id AS tgt,
       (1 - (v.embedding <=> k.embedding))::float8 AS sim
FROM vecs v
CROSS JOIN LATERAL (
    SELECT w.entity_id, w.embedding
    FROM vecs w
    WHERE w.entity_id <> v.entity_id
    ORDER BY w.embedding <=> v.embedding
    LIMIT CAST(:top_k AS int)
) k
WHERE (1 - (v.embedding <=> k.embedding)) >= CAST(:threshold AS float8)
""")


# ── the artefact ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class Snapshot:
    """One project's converged-PageRank-ready graph, held in process.

    `graph` is an `igraph.Graph`; it is typed loosely so importing this module
    never requires the library, which the build path itself treats as optional.
    """

    project: str
    fingerprint: str | None
    entity_ids: tuple[str, ...]
    index_of: Mapping[str, int]
    memory_ids: tuple[tuple[str, ...], ...]
    graph: object
    built_at: float
    relation_edges: int = 0
    synonymy_edges: int = 0
    degraded: tuple[str, ...] = ()

    @property
    def node_count(self) -> int:
        return len(self.entity_ids)

    @property
    def edge_count(self) -> int:
        return self.relation_edges + self.synonymy_edges


@dataclass(frozen=True)
class BuildOutcome:
    project: str
    snapshot: Snapshot | None
    skipped_reason: str | None = None
    duration_ms: int = 0


@dataclass
class RefreshOutcome:
    projects_visited: int = 0
    snapshots_built: int = 0
    skipped: int = 0
    last_project: str | None = None
    outcomes: list[BuildOutcome] = field(default_factory=list)


class SnapshotCache:
    """The one process-global holder, keyed by project.

    Replacement is whole and atomic per project: a rebuild that fails leaves
    the previous snapshot in place rather than emptying the cache, which is the
    same "stale is not corrupt" stance the topic detector takes for its
    per-project rewrite. Emptying on failure would silently retire the arm for
    that project until the next successful run.
    """

    def __init__(self) -> None:
        self._by_project: dict[str, Snapshot] = {}

    def get(self, project: str) -> Snapshot | None:
        return self._by_project.get(project)

    def put(self, snapshot: Snapshot) -> None:
        self._by_project[snapshot.project] = snapshot

    def drop(self, project: str) -> None:
        self._by_project.pop(project, None)

    def clear(self) -> None:
        self._by_project.clear()

    def stats(self) -> dict[str, dict[str, object]]:
        return {
            project: {
                "nodes": snap.node_count,
                "edges": snap.edge_count,
                "built_at": snap.built_at,
                "degraded": list(snap.degraded),
            }
            for project, snap in self._by_project.items()
        }


_CACHE = SnapshotCache()


def snapshot_cache() -> SnapshotCache:
    return _CACHE


# ── building ─────────────────────────────────────────────────────────


def _make_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=1, thread_name_prefix="ppr")


async def build_snapshot(
    session: AsyncSession,
    project: str,
    *,
    fingerprint: str | None = None,
    synonymy_threshold: float = DEFAULT_SYNONYMY_THRESHOLD,
    synonymy_top_k: int = DEFAULT_SYNONYMY_TOP_K,
    synonymy_max_nodes: int = DEFAULT_SYNONYMY_MAX_NODES,
    max_snapshot_edges: int = DEFAULT_MAX_SNAPSHOT_EDGES,
    build_timeout_seconds: float = DEFAULT_BUILD_TIMEOUT_SECONDS,
) -> BuildOutcome:
    """This project's snapshot, or why there is none.

    Reads are ordered so that every fallible *library* step happens after every
    database read has finished, for the reason the topic detector records: a
    build that reads, then fails, must not have already disturbed anything.
    Here nothing is written at all, so the only state a failure can damage is
    the cache — and the caller only replaces it on a returned snapshot.
    """
    started = time.perf_counter()

    def _elapsed_ms() -> int:
        return int((time.perf_counter() - started) * 1000)

    rows = (await session.execute(_NODES_SQL, {"project": project})).all()
    if not rows:
        return BuildOutcome(project, None, SKIPPED_NO_NODES, _elapsed_ms())

    entity_ids = tuple(str(row.entity_id) for row in rows)
    index_of = {eid: i for i, eid in enumerate(entity_ids)}
    memory_ids = tuple(
        tuple(str(mid) for mid in (row.memory_ids or ())) for row in rows
    )

    edge_weights: dict[tuple[int, int], float] = {}

    relation_rows = (
        await session.execute(_RELATION_EDGES_SQL, {"project": project})
    ).all()
    for row in relation_rows:
        pair = _pair(index_of, row.src, row.tgt)
        if pair is not None:
            edge_weights[pair] = edge_weights.get(pair, 0.0) + float(row.weight)
    relation_edges = len(edge_weights)

    degraded: list[str] = []
    synonymy_edges = 0
    if (
        fingerprint
        and synonymy_top_k > 0
        and len(entity_ids) <= synonymy_max_nodes
    ):
        table = child_table("entity_embeddings", fingerprint)
        syn_rows = (
            await session.execute(
                _synonymy_sql(table),
                {
                    "project": project,
                    "fingerprint": fingerprint,
                    "top_k": synonymy_top_k,
                    "threshold": synonymy_threshold,
                },
            )
        ).all()
        for row in syn_rows:
            pair = _pair(index_of, row.src, row.tgt)
            if pair is None:
                continue
            # KNN is asymmetric — b can be among a's k nearest while a is not
            # among b's — so the same undirected pair may arrive once or twice.
            # `max` keeps one edge at the similarity both readings agree is at
            # least true, rather than double-weighting whatever happened to be
            # mutual.
            before = edge_weights.get(pair)
            weight = float(row.sim)
            if before is None:
                edge_weights[pair] = weight
                synonymy_edges += 1
            else:
                edge_weights[pair] = max(before, weight)
    elif fingerprint and synonymy_top_k > 0:
        degraded.append(DEGRADED_SYNONYMY_SKIPPED)

    if len(edge_weights) > max_snapshot_edges:
        logger.warning(
            "PPR snapshot for project %r skipped: %d edges exceeds the %d bound",
            project, len(edge_weights), max_snapshot_edges,
        )
        return BuildOutcome(project, None, SKIPPED_TOO_MANY_EDGES, _elapsed_ms())

    try:
        import igraph
    except ImportError:
        logger.warning("igraph is not installed; the PPR snapshot is unavailable")
        return BuildOutcome(
            project, None, SKIPPED_LIBRARY_UNAVAILABLE, _elapsed_ms()
        )

    edges = list(edge_weights.keys())
    weights = [edge_weights[e] for e in edges]

    # The graph build runs in the executor for the reason `utils/leiden.py`
    # records: at the edge budget it stalls for hundreds of milliseconds, and
    # this process serves capture and retrieval on the same event loop.
    def _build():
        graph = igraph.Graph(n=len(entity_ids), edges=edges, directed=False)
        if weights:
            graph.es["weight"] = weights
        return graph

    executor = _make_executor()
    try:
        loop = asyncio.get_running_loop()
        graph = await asyncio.wait_for(
            loop.run_in_executor(executor, _build), timeout=build_timeout_seconds
        )
    except asyncio.TimeoutError:
        logger.warning(
            "PPR snapshot build for project %r exceeded %.1fs on %d nodes",
            project, build_timeout_seconds, len(entity_ids),
        )
        return BuildOutcome(project, None, "timeout", _elapsed_ms())
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    snapshot = Snapshot(
        project=project,
        fingerprint=fingerprint,
        entity_ids=entity_ids,
        index_of=index_of,
        memory_ids=memory_ids,
        graph=graph,
        built_at=time.time(),
        relation_edges=relation_edges,
        synonymy_edges=synonymy_edges,
        degraded=tuple(degraded),
    )
    return BuildOutcome(project, snapshot, None, _elapsed_ms())


def _pair(
    index_of: Mapping[str, int], src: object, tgt: object
) -> tuple[int, int] | None:
    """The undirected edge key, or ``None`` if either endpoint left the node set.

    Normalised low-index-first so the two directions of one relation, and the
    two readings of one KNN neighbourhood, land on the same key. Keying on the
    raw ordered pair instead would give a single conceptual edge two entries
    with half its weight each — the same shape invariant 9's id drift takes,
    and just as silent.
    """
    i = index_of.get(str(src))
    j = index_of.get(str(tgt))
    if i is None or j is None or i == j:
        return None
    return (i, j) if i < j else (j, i)


# ── spending it ──────────────────────────────────────────────────────


def seed_vertices_for_memories(
    snapshot: Snapshot, memory_ids: Iterable[str]
) -> list[int]:
    """The vertices to seed PPR from, given the memories a channel already found.

    Doc 07 §11 offers two seedings — entities matched from the query embedding,
    or the entities of the top-K memory-semantic hits. This takes the second,
    and the choice is not only about cost: the first needs a second ANN probe
    on the query path, while this reads a mapping the snapshot already holds,
    so an active arm adds no query-time database read at all (invariant 15).
    """
    wanted = {str(m) for m in memory_ids}
    if not wanted:
        return []
    return [
        i
        for i, mids in enumerate(snapshot.memory_ids)
        if any(mid in wanted for mid in mids)
    ]


def personalized_pagerank(
    snapshot: Snapshot,
    seeds: Sequence[int],
    *,
    damping: float = DEFAULT_DAMPING,
) -> list[float]:
    """Converged PPR mass per vertex, seeded uniformly over ``seeds``.

    An empty seed set returns no mass rather than falling back to uniform
    PageRank: a global-popularity list fused into every query is a *different
    signal* wearing this one's name, and it would rank the project's hub
    entities into every result set regardless of the query.
    """
    if not seeds:
        return [0.0] * snapshot.node_count
    graph = snapshot.graph
    weights = "weight" if graph.ecount() and "weight" in graph.es.attributes() else None
    return list(
        graph.personalized_pagerank(
            damping=damping, reset_vertices=list(seeds), weights=weights,
        )
    )


def rank_memories(snapshot: Snapshot, mass: Sequence[float]) -> list[dict]:
    """Entity mass projected onto memories, ranked.

    A memory's score is the sum of the mass of the entities that assert it, and
    a memory asserting more of the mass-carrying entities outranks one
    asserting fewer. Rows are shaped like every other ranked producer's
    (`memory_id` as ``str``, `score`) so `normalize_row_id` needs no special
    case — invariant 9 is settled at construction rather than at the fusion.
    """
    totals: dict[str, float] = {}
    for i, m in enumerate(mass):
        if m <= 0.0:
            continue
        for mid in snapshot.memory_ids[i]:
            totals[mid] = totals.get(mid, 0.0) + m
    ordered = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"memory_id": mid, "score": score} for mid, score in ordered]


async def ppr_ranked_list(
    project: str | None,
    seed_memory_ids: Iterable[str],
    *,
    limit: int,
    damping: float = DEFAULT_DAMPING,
    cache: SnapshotCache | None = None,
) -> list[dict]:
    """The PPR arm's ranked list, or an empty one.

    Empty — never an exception — whenever the arm has nothing to say: no
    project scope, no snapshot for it yet, or no seed entity in it. The arm is
    an augmentation, so its absence must cost the fused order nothing.
    """
    if not project:
        return []
    snapshot = (cache or _CACHE).get(project)
    if snapshot is None:
        return []
    seeds = seed_vertices_for_memories(snapshot, seed_memory_ids)
    if not seeds:
        return []

    executor = _make_executor()
    try:
        loop = asyncio.get_running_loop()
        mass = await loop.run_in_executor(
            executor, lambda: personalized_pagerank(snapshot, seeds, damping=damping)
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return rank_memories(snapshot, mass)[:limit]


# ── the Tier-C refresh ───────────────────────────────────────────────

_NEXT_PROJECTS = text(
    """
    SELECT DISTINCT project
    FROM memories
    WHERE status = 'active'
      AND is_archived = false
      AND (expires_at IS NULL OR expires_at > now())
      AND (project > CAST(:after_project AS text)
           OR CAST(:after_project AS text) IS NULL)
    ORDER BY project
    LIMIT CAST(:batch_size AS int)
    """
)


async def next_projects(
    session: AsyncSession, after_project: str | None, batch_size: int
) -> list[str]:
    return [
        row[0]
        for row in await session.execute(
            _NEXT_PROJECTS,
            {"after_project": after_project, "batch_size": batch_size},
        )
    ]


async def refresh_snapshots(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    fingerprint: str | None = None,
    batch_size: int = DEFAULT_PROJECT_BATCH,
    after_project: str | None = None,
    cache: SnapshotCache | None = None,
    **build_kwargs,
) -> RefreshOutcome:
    """Rebuild a bounded rotation of projects' snapshots.

    One session per project rather than one per run, for the reason the topic
    detector records: a whole-run session would make one project's bad graph
    everyone's problem, and these reads are long enough that holding a single
    connection across the rotation matters.
    """
    target = cache or _CACHE
    outcome = RefreshOutcome()

    async with session_factory() as session:
        projects = await next_projects(session, after_project, batch_size)

    for project in projects:
        outcome.projects_visited += 1
        outcome.last_project = project
        try:
            async with session_factory() as session:
                built = await build_snapshot(
                    session, project, fingerprint=fingerprint, **build_kwargs
                )
        except Exception:
            logger.exception("PPR snapshot build failed for project %r", project)
            outcome.skipped += 1
            continue

        outcome.outcomes.append(built)
        if built.snapshot is None:
            outcome.skipped += 1
            continue
        target.put(built.snapshot)
        outcome.snapshots_built += 1

    return outcome

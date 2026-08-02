"""The project-scoped memory projection topics are clustered over (doc 06 §7).

Nodes are **memories**, because `memory_community_members` keys on `memory_id`
and nothing else is representable. Edges are derived, never stored: two
memories are adjacent when they assert a shared entity, and the edge's weight
is Newman's collaboration-projection normaliser over the entities they share.

**Why the weight is not 1.** An unweighted projection makes two memories
sharing one incidental `concept` as connected as two sharing eight specific
tools, and a hub entity (`postgres`, `darkmem`, `python`) injects a clique of
`n(n-1)/2` unit-weight edges that collapses a whole project into one blob while
reporting success. `1/(n_e - 1)` spreads each entity's contribution over its
clique, so specificity buys connection and ubiquity does not; `hub_cap` is a
separate, non-interchangeable *materialisation* bound, because normalising the
score of 124 750 rows still materialises 124 750 rows.

`n_e` is counted **after** restricting to the project's eligible node set. An
entity that is a hub across the whole install but is asserted by three memories
inside this project is specific *here* and should weigh like a rare entity here.

**Eligibility is the live set, spelled the way the schema already spells it.**
`status = 'active' AND is_archived = false` is `ix_memories_project_live`'s own
predicate. The `expires_at` clause is the load-bearing third: sweeping is
periodic, so an expired-but-unswept row is still `status='active'`, and doc 06
§7's lifecycle routes "expired out" of a community.

**Composition.** Edge arms accumulate into one `(u, v) -> weight` map, so a
second arm (doc 06's `memory_relations`, once T2.12 writes any) is a union with
weight addition over the same node set rather than a redefinition of this one.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_HUB_CAP = 200
DEFAULT_MAX_PROJECTION_EDGES = 2_000_000
DEFAULT_EXCLUDED_ENTITY_TYPES: tuple[str, ...] = ()

TRUNCATED_TOO_MANY_EDGES = "max_projection_edges"

# `AS MATERIALIZED` on `eligible` for the reason the buffer-claim CTE records
# in CLAUDE.md: a plain sub-select lets the planner re-execute it per outer
# row, which here means quadratic re-evaluation against `memories`.
_PROJECTION_CTES = """
WITH eligible AS MATERIALIZED (
    SELECT id
    FROM memories
    WHERE project = CAST(:project AS text)
      AND status = 'active'
      AND is_archived = false
      AND (expires_at IS NULL OR expires_at > now())
),
asserted AS MATERIALIZED (
    SELECT e.id AS entity_id, el.id AS memory_id
    FROM entities e
    JOIN LATERAL unnest(e.memory_ids) AS u(mid) ON TRUE
    JOIN eligible el ON el.id = u.mid
    WHERE e.entity_type <> ALL (CAST(:excluded_types AS text[]))
),
sized AS (
    SELECT entity_id, count(*) AS n
    FROM asserted
    GROUP BY entity_id
    HAVING count(*) >= 2 AND count(*) <= CAST(:hub_cap AS int)
)
"""

_NODES = text(
    """
    SELECT id
    FROM memories
    WHERE project = CAST(:project AS text)
      AND status = 'active'
      AND is_archived = false
      AND (expires_at IS NULL OR expires_at > now())
    ORDER BY id
    """
)

# The pair count before the edge list is materialised: an upper bound on the
# distinct edges, since several entities may share one pair.
_EDGE_BUDGET = text(
    _PROJECTION_CTES
    + "SELECT COALESCE(sum(s.n * (s.n - 1) / 2), 0) AS pairs FROM sized s"
)

_ENTITY_EDGE_ARM = text(
    _PROJECTION_CTES
    + """
    SELECT a.memory_id AS u, b.memory_id AS v, sum(1.0 / (s.n - 1)) AS w
    FROM asserted a
    JOIN asserted b ON b.entity_id = a.entity_id AND a.memory_id < b.memory_id
    JOIN sized s ON s.entity_id = a.entity_id
    GROUP BY a.memory_id, b.memory_id
    ORDER BY a.memory_id, b.memory_id
    """
)

_ENTITY_INDEX = text(
    _PROJECTION_CTES
    + """
    SELECT s.entity_id,
           e.name,
           e.entity_type,
           e.properties->>'display_name' AS display_name,
           s.n AS n_e,
           array_agg(a.memory_id ORDER BY a.memory_id) AS memory_ids
    FROM sized s
    JOIN entities e ON e.id = s.entity_id
    JOIN asserted a ON a.entity_id = s.entity_id
    GROUP BY s.entity_id, e.name, e.entity_type, e.properties, s.n
    ORDER BY e.name, s.entity_id
    """
)


@dataclass(frozen=True)
class EntityAssertion:
    """One entity that survived `sized`, and which nodes assert it.

    `member_indices` are indices into `Projection.node_ids`, never raw ids —
    the same closure that makes a foreign memory unnameable by the partition.
    """

    entity_id: UUID
    name: str
    display_name: str | None
    entity_type: str
    n_e: int
    member_indices: tuple[int, ...]

    @property
    def rendered(self) -> str:
        """Original casing where the pipeline preserved it (invariant 7)."""
        return self.display_name or self.name


@dataclass(frozen=True)
class Projection:
    project: str
    node_ids: tuple[UUID, ...]
    edges: tuple[tuple[int, int, float], ...]
    entity_index: tuple[EntityAssertion, ...]
    truncated_reason: str | None = None

    @property
    def node_count(self) -> int:
        return len(self.node_ids)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def connected_indices(self) -> tuple[int, ...]:
        """Node indices carrying at least one edge, in node order.

        A memory sharing no entity with anything is not topically related to
        anything, so the fallbacks cover these rather than sweeping isolated
        nodes into an everything-community.
        """
        touched: set[int] = set()
        for u, v, _ in self.edges:
            touched.add(u)
            touched.add(v)
        return tuple(sorted(touched))


async def build_projection(
    session: AsyncSession,
    project: str,
    *,
    hub_cap: int = DEFAULT_HUB_CAP,
    excluded_types: tuple[str, ...] = DEFAULT_EXCLUDED_ENTITY_TYPES,
    max_projection_edges: int = DEFAULT_MAX_PROJECTION_EDGES,
) -> Projection:
    params = {
        "project": project,
        "hub_cap": hub_cap,
        "excluded_types": list(excluded_types),
    }

    node_rows = await session.execute(_NODES, {"project": project})
    node_ids = tuple(row[0] for row in node_rows)
    index_of = {memory_id: idx for idx, memory_id in enumerate(node_ids)}

    if len(node_ids) < 2:
        return Projection(project, node_ids, (), ())

    budget = await session.scalar(_EDGE_BUDGET, params)
    if int(budget or 0) > max_projection_edges:
        # Truncating to the top-N edges would change the clustering semantics
        # with no error and no symptom, which is the failure shape the code
        # side's `index_debt` exists to prevent. Skip loudly instead.
        return Projection(
            project, node_ids, (), (), truncated_reason=TRUNCATED_TOO_MANY_EDGES
        )

    edge_totals: dict[tuple[int, int], float] = {}
    arm = await session.execute(_ENTITY_EDGE_ARM, params)
    for row in arm.mappings():
        pair = (index_of[row["u"]], index_of[row["v"]])
        edge_totals[pair] = edge_totals.get(pair, 0.0) + float(row["w"])

    edges = tuple(
        (u, v, weight) for (u, v), weight in sorted(edge_totals.items())
    )

    index_rows = await session.execute(_ENTITY_INDEX, params)
    entity_index = tuple(
        EntityAssertion(
            entity_id=row["entity_id"],
            name=row["name"],
            display_name=row["display_name"],
            entity_type=row["entity_type"],
            n_e=int(row["n_e"]),
            member_indices=tuple(index_of[mid] for mid in row["memory_ids"]),
        )
        for row in index_rows.mappings()
    )

    return Projection(project, node_ids, edges, entity_index)

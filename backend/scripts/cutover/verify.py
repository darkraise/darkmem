"""The two verification legs, plus the positive assertions.

Data reaches the target over two legs — source to staging, which is
Python-mediated, and staging to target, which is pure SQL. A defect on the
first leg corrupts staging and the target *identically*, so a staging-to-target
comparison is a corrupted value agreeing with itself and every check passes.
Both legs are therefore checked, and the source leg runs before the first
carried-table write so a driver-level defect stops the run before anything
is written.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import asyncpg

from . import spec

_SENTINEL_LITERAL = "'" + spec.NULL_SENTINEL + "'"


def _column_ref(name: str) -> str:
    return f'"{name}"'


def _checksum_expression(column: spec.Column, name: str) -> str:
    """Timestamps checksum as epoch, never as text.

    A timestamptz rendered as text depends on the session TimeZone, and the two
    sides of the source-to-staging comparison are different sessions on
    different databases. The GUCs are pinned as well; this removes the member
    rather than relying on the class fix alone.
    """
    ref = _column_ref(name)
    if column.is_timestamp:
        return f"extract(epoch from {ref})::text"
    return f"{ref}::text"


def aggregate_sql(table: spec.CarriedTable, relation: str, *, target_names: bool) -> str:
    order = ", ".join(_column_ref(k) for k in table.key)
    parts = ["count(*)::bigint AS row_count"]
    for index, column in enumerate(table.columns):
        name = column.target if target_names else column.source
        ref = _column_ref(name)
        expr = _checksum_expression(column, name)
        parts.append(
            f"md5(string_agg(COALESCE({expr}, {_SENTINEL_LITERAL}), '|' ORDER BY {order}))"
            f" AS ck_{index}"
        )
        parts.append(f"count(*) FILTER (WHERE {ref} IS NULL)::bigint AS null_{index}")
        parts.append(f"count(DISTINCT {ref})::bigint AS dist_{index}")
    return f'SELECT {", ".join(parts)} FROM "{relation}"'


LINEAGE_PAIRS_SQL = (
    "SELECT md5(string_agg("
    f"id::text || '>' || COALESCE(superseded_by::text, {_SENTINEL_LITERAL}), "
    "'|' ORDER BY id)) AS pairs FROM \"{relation}\""
)

STATUS_BREAKDOWN_SQL = (
    'SELECT status::text AS status, count(*)::bigint AS n FROM "{relation}" '
    "GROUP BY 1 ORDER BY 1"
)


@dataclass
class TableAggregate:
    table: str
    relation: str
    row_count: int
    columns: dict[str, dict[str, object]] = field(default_factory=dict)
    lineage_pairs: str | None = None
    status_breakdown: dict[str, int] | None = None

    def to_dict(self) -> dict:
        return {
            "table": self.table,
            "relation": self.relation,
            "row_count": self.row_count,
            "columns": self.columns,
            "lineage_pairs": self.lineage_pairs,
            "status_breakdown": self.status_breakdown,
        }


async def table_aggregate(
    conn: asyncpg.Connection,
    table: spec.CarriedTable,
    relation: str,
    *,
    target_names: bool,
) -> TableAggregate:
    row = await conn.fetchrow(aggregate_sql(table, relation, target_names=target_names))
    aggregate = TableAggregate(
        table=table.name, relation=relation, row_count=row["row_count"]
    )
    for index, column in enumerate(table.columns):
        aggregate.columns[column.source] = {
            "checksum": row[f"ck_{index}"],
            "nulls": row[f"null_{index}"],
            "distinct": row[f"dist_{index}"],
        }
    if table.name == "memories":
        aggregate.lineage_pairs = await conn.fetchval(
            LINEAGE_PAIRS_SQL.format(relation=relation)
        )
        breakdown = await conn.fetch(STATUS_BREAKDOWN_SQL.format(relation=relation))
        aggregate.status_breakdown = {r["status"]: r["n"] for r in breakdown}
    return aggregate


async def aggregate_side(
    conn: asyncpg.Connection, *, staging: bool = False, target_names: bool = False
) -> dict[str, TableAggregate]:
    result: dict[str, TableAggregate] = {}
    for table in spec.CARRIED:
        relation = table.staging_name if staging else table.name
        result[table.name] = await table_aggregate(
            conn, table, relation, target_names=target_names
        )
    return result


def compare_aggregates(
    left_label: str,
    right_label: str,
    left: dict[str, TableAggregate],
    right: dict[str, TableAggregate],
) -> list[str]:
    """Return one message per mismatch. An empty list is the only pass."""
    problems: list[str] = []
    for table in spec.CARRIED:
        a, b = left[table.name], right[table.name]
        if a.row_count != b.row_count:
            problems.append(
                f"{table.name}: row count {left_label}={a.row_count} "
                f"{right_label}={b.row_count}"
            )
        for column in table.columns:
            left_col = a.columns[column.source]
            right_col = b.columns[column.source]
            # A NULL checksum can only come from a zero-row relation once the
            # COALESCE sentinel is in place; anywhere else it means the
            # aggregate did not run, and None == None would pass silently.
            if a.row_count and (
                left_col["checksum"] is None or right_col["checksum"] is None
            ):
                problems.append(
                    f"{table.name}.{column.source}: NULL checksum over "
                    f"{a.row_count} rows ({left_label}={left_col['checksum']!r} "
                    f"{right_label}={right_col['checksum']!r})"
                )
                continue
            for key in ("checksum", "nulls", "distinct"):
                if left_col[key] != right_col[key]:
                    problems.append(
                        f"{table.name}.{column.source}: {key} "
                        f"{left_label}={left_col[key]!r} {right_label}={right_col[key]!r}"
                    )
        if a.lineage_pairs != b.lineage_pairs:
            problems.append(
                f"{table.name}: lineage pair set {left_label}={a.lineage_pairs!r} "
                f"{right_label}={b.lineage_pairs!r}"
            )
        if a.status_breakdown != b.status_breakdown:
            problems.append(
                f"{table.name}: status breakdown {left_label}={a.status_breakdown} "
                f"{right_label}={b.status_breakdown}"
            )
    return problems


async def positive_assertions(target: asyncpg.Connection) -> tuple[dict, list[str]]:
    """The three things the transform's own design requires to be true.

    An empty technologies proves a stale derivation was not carried. A populated
    search_vector proves the FTS trigger fired — had it not, carried rows would
    be invisible to hybrid search's keyword arm while the semantic arm still
    returned them, silently degrading RRF with no error anywhere. A NULL
    origin_key is the T1.11 rule applied to history.
    """
    row = await target.fetchrow(
        """
        SELECT count(*)::bigint                                              AS total,
               count(*) FILTER (WHERE technologies <> '{}'::text[])::bigint  AS technologies_not_empty,
               count(*) FILTER (WHERE search_vector IS NULL)::bigint         AS search_vector_null,
               count(*) FILTER (WHERE origin_key IS NOT NULL)::bigint        AS origin_key_not_null
        FROM memories
        """
    )
    measured = dict(row)
    problems = []
    if row["technologies_not_empty"]:
        problems.append(
            f"{row['technologies_not_empty']} carried memories have a non-empty "
            "technologies; it is rebuilt, never carried"
        )
    if row["search_vector_null"]:
        problems.append(
            f"{row['search_vector_null']} carried memories have a NULL search_vector; "
            "the FTS trigger did not fire"
        )
    if row["origin_key_not_null"]:
        problems.append(
            f"{row['origin_key_not_null']} carried memories have a non-NULL origin_key; "
            "history is not evidence of independence"
        )
    return measured, problems


async def post_seed_assertions(target: asyncpg.Connection) -> tuple[dict, list[str]]:
    """Verify the sequence advance and the projects seed.

    Without the setval the first tag created after the cutover collides on the
    primary key — loud when it happens, and it happens after verification is
    green, so a count-based check cannot see it.
    """
    problems: list[str] = []
    max_tag_id = await target.fetchval("SELECT max(id) FROM tags")
    last_value = await target.fetchval("SELECT last_value FROM tags_id_seq")
    if max_tag_id is not None and last_value < max_tag_id:
        problems.append(
            f"tags_id_seq.last_value={last_value} is below max(tags.id)={max_tag_id}"
        )

    uncovered = await target.fetch(
        "SELECT DISTINCT m.project FROM memories m "
        "LEFT JOIN projects p ON p.name = m.project "
        "WHERE p.name IS NULL ORDER BY 1"
    )
    if uncovered:
        problems.append(
            "projects has no row for: " + ", ".join(r["project"] for r in uncovered)
        )

    # Reported, never deleted: --reset does not clear projects, so a project
    # from an earlier run's carried set survives. It is inert — no FK, and
    # nothing reads a project row no memory references — and deleting it would
    # be the tool silently removing a row it did not create.
    stale = await target.fetch(
        "SELECT p.name FROM projects p "
        "LEFT JOIN memories m ON m.project = p.name "
        "WHERE m.id IS NULL ORDER BY 1"
    )
    measured = {
        "max_tag_id": max_tag_id,
        "tags_id_seq_last_value": last_value,
        "projects_without_memories": [r["name"] for r in stale],
    }
    return measured, problems

"""ml_pipeline_taxonomy_migration

Rewrites legacy entity_type and rel_type values to the consolidated 10-type
taxonomy used by the ML extraction heads (see app.taxonomy).

Downgrade is a no-op because the collapse is lossy — many old types map
onto a single new type and the original split cannot be reconstructed.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-18
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text


revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Legacy entity_type values that need renaming. Kept inline on purpose —
# Alembic migrations are the authoritative history for schema state and
# should not import from application code (which evolves independently).
LEGACY_ENTITY_TYPE_MAP: dict[str, str] = {
    "person": "entity",
    "organization": "entity",
    "team": "entity",
    "company": "entity",
    "date": "entity",
    "place": "entity",
    "event": "entity",
    "technology": "tool",
    "framework": "tool",
    "library": "tool",
    "pattern": "tool",
    "platform": "service",
    "infrastructure": "service",
    "api": "service",
    "system": "service",
    "standard": "protocol",
    "specification": "protocol",
    "method": "algorithm",
    "file": "artifact",
    "command": "artifact",
    "config": "artifact",
    "error": "artifact",
    "theory": "concept",
    "field": "concept",
    "publication": "concept",
    "finding": "concept",
    "claim": "concept",
    "data structure": "concept",
    "approach": "concept",
    "constant": "concept",
}


LEGACY_RELATION_TYPE_MAP: dict[str, str] = {
    "CONFIGURES": "USES",
    "APPLIES_TO": "USES",
    "COMMUNICATES_WITH": "USES",
    "IMPLEMENTS": "USES",
    "IMPROVES_ON": "REPLACES",
    "BUILDS_ON": "REPLACES",
    "EXTENDS": "HAS_PART",
    "LOCATED_IN": "DEPLOYED_ON",
    "PRODUCES": "CAUSES",
    "FIXES": "CAUSES",
    "PUBLISHED_IN": "AUTHORED_BY",
    "WORKS_AT": "AUTHORED_BY",
    "VISITED": "HAPPENED_ON",
    "LIVES_IN": "HAPPENED_ON",
    "ALTERNATIVE_TO": "RELATED_TO",
    "KNOWS": "RELATED_TO",
    "SUPPORTS": "RELATED_TO",
    "CONTRADICTS": "RELATED_TO",
    "PREFERS": "RELATED_TO",
    "FEELS_ABOUT": "RELATED_TO",
    "PLANS_TO": "RELATED_TO",
}


def _rename_entities(conn, old: str, new: str) -> tuple[int, int]:
    """Rename ``entities.entity_type`` from ``old`` to ``new`` while merging
    any rows that would collide with an existing ``(name, new)`` row.

    Merge strategy: union memory_ids into the surviving row, drop the old one,
    then rename whatever is left. Returns ``(merged, renamed)`` row counts.

    The first statement is a data-modifying CTE: the UPDATE unions memory_ids
    into the winning (name, :new) rows and returns the ids of their losing
    twins, and the outer DELETE removes exactly those losers. Postgres runs
    every CTE against the same snapshot (see the docs on data-modifying CTEs),
    so the DELETE consumes the RETURNING rowset rather than observing the
    UPDATE's row changes directly — which is what we want here: the UPDATE
    has already transferred state, the DELETE only has to retire the row.

    The subsequent plain UPDATE then renames all remaining rows with
    entity_type = :old, which are guaranteed to have no collision on
    (name, :new) because the merge CTE just removed every such pair.
    """
    merge_result = conn.execute(
        text(
            """
            WITH pairs AS (
                SELECT e_old.id AS old_id,
                       e_new.id AS new_id,
                       e_old.memory_ids AS old_mids
                FROM entities e_old
                JOIN entities e_new
                  ON e_new.name = e_old.name AND e_new.entity_type = :new
                WHERE e_old.entity_type = :old
            ),
            merged AS (
                UPDATE entities e_new
                SET memory_ids = (
                    SELECT ARRAY(
                        SELECT DISTINCT unnest(
                            COALESCE(e_new.memory_ids, '{}'::uuid[]) ||
                            COALESCE(p.old_mids, '{}'::uuid[])
                        )
                    )
                )
                FROM pairs p
                WHERE e_new.id = p.new_id
                RETURNING p.old_id
            )
            DELETE FROM entities
            WHERE id IN (SELECT old_id FROM merged)
            """
        ),
        {"old": old, "new": new},
    )
    merged = merge_result.rowcount or 0

    rename_result = conn.execute(
        text("UPDATE entities SET entity_type = :new WHERE entity_type = :old"),
        {"old": old, "new": new},
    )
    renamed = rename_result.rowcount or 0
    return merged, renamed


def _rename_relations(conn, old: str, new: str) -> tuple[int, int]:
    """Rename ``entity_relations.rel_type`` from ``old`` to ``new`` while
    merging collisions on ``(source_entity_id, target_entity_id, rel_type)``.

    Winning row takes the max weight and the union of memory_ids. Uses the
    same data-modifying-CTE pattern as :func:`_rename_entities`; see that
    docstring for the snapshot semantics.
    """
    merge_result = conn.execute(
        text(
            """
            WITH pairs AS (
                SELECT r_old.id AS old_id,
                       r_new.id AS new_id,
                       r_old.memory_ids AS old_mids,
                       r_old.weight AS old_weight
                FROM entity_relations r_old
                JOIN entity_relations r_new
                  ON r_new.source_entity_id = r_old.source_entity_id
                 AND r_new.target_entity_id = r_old.target_entity_id
                 AND r_new.rel_type = :new
                WHERE r_old.rel_type = :old
            ),
            merged AS (
                UPDATE entity_relations r_new
                SET memory_ids = (
                        SELECT ARRAY(
                            SELECT DISTINCT unnest(
                                COALESCE(r_new.memory_ids, '{}'::uuid[]) ||
                                COALESCE(p.old_mids, '{}'::uuid[])
                            )
                        )
                    ),
                    weight = GREATEST(COALESCE(r_new.weight, 0), COALESCE(p.old_weight, 0))
                FROM pairs p
                WHERE r_new.id = p.new_id
                RETURNING p.old_id
            )
            DELETE FROM entity_relations
            WHERE id IN (SELECT old_id FROM merged)
            """
        ),
        {"old": old, "new": new},
    )
    merged = merge_result.rowcount or 0

    rename_result = conn.execute(
        text("UPDATE entity_relations SET rel_type = :new WHERE rel_type = :old"),
        {"old": old, "new": new},
    )
    renamed = rename_result.rowcount or 0
    return merged, renamed


def upgrade() -> None:
    conn = op.get_bind()

    entity_merges = 0
    entity_renames = 0
    for old, new in LEGACY_ENTITY_TYPE_MAP.items():
        if old == new:
            continue
        merged, renamed = _rename_entities(conn, old, new)
        if merged or renamed:
            print(f"entity_type {old!r} -> {new!r}: merged={merged} renamed={renamed}")
        entity_merges += merged
        entity_renames += renamed

    relation_merges = 0
    relation_renames = 0
    for old, new in LEGACY_RELATION_TYPE_MAP.items():
        if old == new:
            continue
        merged, renamed = _rename_relations(conn, old, new)
        if merged or renamed:
            print(f"rel_type {old!r} -> {new!r}: merged={merged} renamed={renamed}")
        relation_merges += merged
        relation_renames += renamed

    print(
        "taxonomy migration summary: "
        f"entity_merges={entity_merges} entity_renames={entity_renames} "
        f"relation_merges={relation_merges} relation_renames={relation_renames}"
    )


def downgrade() -> None:
    # Type collapse is lossy (N-to-1). No-op by design; drop the 0004
    # revision marker only if you are restoring a pre-migration backup.
    pass

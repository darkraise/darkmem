"""The transform and the load, plus the ``--reset`` guard.

The five loads are one ``INSERT … SELECT`` per table and never a batched or
row-wise loop. ``fk_memories_superseded_by`` is not declared DEFERRABLE, so
``SET CONSTRAINTS ALL DEFERRED`` does not apply to it; a forward reference
inside a single statement succeeds because non-deferrable FK triggers fire at
end of statement, and the same reference row-at-a-time fails. A batched load
therefore passes every small fixture and fails only where a supersession
pointer crosses a batch boundary — non-deterministically in batch size and row
order.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import asyncpg

from . import spec
from .db import CutoverError


def load_sql(table: spec.CarriedTable) -> str:
    columns = list(table.target_columns) + [name for name, _ in table.target_only]
    expressions = [
        table.load_expressions.get(column.source, f's."{column.source}"')
        for column in table.columns
    ]
    expressions += [expression for _, expression in table.target_only]
    column_list = ", ".join(f'"{c}"' for c in columns)
    return (
        f'INSERT INTO "{table.name}" ({column_list})\n'
        f'SELECT {", ".join(expressions)}\n'
        f'FROM "{table.staging_name}" s'
    )


async def load_table(target: asyncpg.Connection, table: spec.CarriedTable) -> None:
    await target.execute(load_sql(table))


async def load_all(target: asyncpg.Connection) -> None:
    for table in spec.CARRIED:
        await load_table(target, table)


# setval is non-transactional and is not rolled back. It runs after the parity
# checks for that reason: a value-level abort then leaves literally zero
# residue rather than an advanced sequence.
SETVAL_SQL = (
    "SELECT setval('tags_id_seq', COALESCE((SELECT max(id) FROM tags), 1), "
    "(SELECT count(*) > 0 FROM tags))"
)

# ON CONFLICT DO NOTHING rather than a bare INSERT: --reset does not delete
# projects, so a bare insert would raise a spurious PK violation on the second
# run. The row it declines to write is byte-identical to the row already there,
# because projects.name is the whole key.
SEED_PROJECTS_SQL = (
    "INSERT INTO projects (name) SELECT DISTINCT project FROM memories "
    "ON CONFLICT (name) DO NOTHING"
)


async def advance_tag_sequence(target: asyncpg.Connection) -> int:
    return await target.fetchval(SETVAL_SQL)


async def seed_projects(target: asyncpg.Connection) -> str:
    return await target.execute(SEED_PROJECTS_SQL)


@dataclass
class ResetGuardResult:
    unknown: dict[str, int] = field(default_factory=dict)
    edited: dict[str, int] = field(default_factory=dict)
    unknown_samples: dict[str, list] = field(default_factory=dict)
    edited_samples: dict[str, list] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.unknown.values()) + sum(self.edited.values())

    @property
    def clean(self) -> bool:
        return self.total == 0

    def to_dict(self) -> dict:
        return {
            "unknown": self.unknown,
            "edited": self.edited,
            "unknown_samples": self.unknown_samples,
            "edited_samples": self.edited_samples,
            "total": self.total,
        }


MAX_REPORTED_ROWS = 50


async def reset_dump_membership(target: asyncpg.Connection) -> ResetGuardResult:
    """Ask the exact question rather than a proxy for it.

    Staging is already populated when this runs, so the guard can ask whether
    the target holds a row the dump never contained — which catches a
    post-cutover capture with a backdated ``created_at``, and catches a reset
    pointed at a *different* dump, neither of which a max-timestamp comparison
    sees. A post-cutover *edit* keeps its id, so the id check cannot see it;
    the ``updated_at`` high-water check is what covers that.
    """
    result = ResetGuardResult()
    for table in spec.CARRIED:
        predicate = " AND ".join(f's."{k}" = t."{k}"' for k in table.key)
        key_list = ", ".join(f't."{k}"' for k in table.key)
        count = await target.fetchval(
            f'SELECT count(*) FROM "{table.name}" t '
            f'WHERE NOT EXISTS (SELECT 1 FROM "{table.staging_name}" s WHERE {predicate})'
        )
        if count:
            result.unknown[table.name] = count
            rows = await target.fetch(
                f'SELECT {key_list} FROM "{table.name}" t '
                f'WHERE NOT EXISTS (SELECT 1 FROM "{table.staging_name}" s WHERE {predicate}) '
                f"LIMIT {MAX_REPORTED_ROWS}"
            )
            result.unknown_samples[table.name] = [
                {k: str(r[k]) for k in table.key} for r in rows
            ]

    for name in spec.RESET_EDIT_CHECK_TABLES:
        table = spec.CARRIED_BY_NAME[name]
        predicate = " AND ".join(f's."{k}" = t."{k}"' for k in table.key)
        key_list = ", ".join(f't."{k}"' for k in table.key)
        where = f'{predicate} AND t."updated_at" > s."updated_at"'
        count = await target.fetchval(
            f'SELECT count(*) FROM "{name}" t, "{table.staging_name}" s WHERE {where}'
        )
        if count:
            result.edited[name] = count
            rows = await target.fetch(
                f'SELECT {key_list} FROM "{name}" t, "{table.staging_name}" s '
                f"WHERE {where} LIMIT {MAX_REPORTED_ROWS}"
            )
            result.edited_samples[name] = [{k: str(r[k]) for k in table.key} for r in rows]
    return result


def assert_reset_allowed(guard: ResetGuardResult, acknowledged: int | None) -> None:
    if guard.clean:
        return
    if acknowledged is not None and acknowledged == guard.total:
        return
    raise CutoverError(
        "--reset refused: the target holds "
        f"{guard.total} row(s) this dump does not account for.\n"
        f"  rows absent from the dump: {guard.unknown or '{}'}\n"
        f"  rows edited since the dump: {guard.edited or '{}'}\n"
        f"  samples (absent): {guard.unknown_samples or '{}'}\n"
        f"  samples (edited): {guard.edited_samples or '{}'}\n"
        "Reloading the dump would destroy them. To proceed anyway, re-run with "
        f"--i-know-rows-will-be-lost {guard.total}"
    )


async def reset_delete(target: asyncpg.Connection) -> dict[str, int]:
    deleted: dict[str, int] = {}
    for name in spec.RESET_DELETE_ORDER:
        status = await target.execute(f'DELETE FROM "{name}"')
        deleted[name] = int(status.rsplit(" ", 1)[-1])
    return deleted

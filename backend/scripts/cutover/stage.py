"""Streaming the source into unlogged staging tables inside the target.

Staging exists for two reasons. It makes the constrained load one statement per
table over an arbitrarily large source, which the non-deferrable
``fk_memories_superseded_by`` requires; and it gives the verification a
same-database "before" side, with no cross-database join and no foreign-data
wrapper carrying credentials.

No transform happens here: staging carries source column names verbatim, so the
transform reads as one auditable SELECT list and the source-to-staging parity
check compares like with like.
"""
from __future__ import annotations

import asyncpg

from . import spec

DEFAULT_BATCH_SIZE = 2_000


async def create_staging_tables(target: asyncpg.Connection) -> None:
    for table in spec.CARRIED:
        columns = ", ".join(f'"{c.source}" {c.staging_type}' for c in table.columns)
        await target.execute(f'DROP TABLE IF EXISTS "{table.staging_name}"')
        await target.execute(f'CREATE UNLOGGED TABLE "{table.staging_name}" ({columns})')


async def drop_staging_tables(target: asyncpg.Connection) -> None:
    for table in spec.CARRIED:
        await target.execute(f'DROP TABLE IF EXISTS "{table.staging_name}"')


async def stream_table(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    table: spec.CarriedTable,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    columns = list(table.source_columns)
    select = ", ".join(f'"{c}"' for c in columns)
    order = ", ".join(f'"{k}"' for k in table.key)
    query = f'SELECT {select} FROM "{table.name}" ORDER BY {order}'

    total = 0
    batch: list[tuple] = []
    async with source.transaction():
        async for record in source.cursor(query, prefetch=batch_size):
            batch.append(tuple(record))
            if len(batch) >= batch_size:
                await target.copy_records_to_table(
                    table.staging_name, records=batch, columns=columns
                )
                total += len(batch)
                batch = []
    if batch:
        await target.copy_records_to_table(
            table.staging_name, records=batch, columns=columns
        )
        total += len(batch)
    return total


async def stage_all(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, int]:
    await create_staging_tables(target)
    return {
        table.name: await stream_table(source, target, table, batch_size)
        for table in spec.CARRIED
    }

"""Connections, and the three structural guards on the source side.

No module in this package may register an asyncpg type codec. Under asyncpg's
default codecs a carried ``jsonb`` value round-trips as an opaque ``str`` and is
byte-identical afterwards; install a ``json.loads``/``json.dumps`` codec and a
numeric past a double's precision comes back rounded, because Postgres stores
jsonb numerics as arbitrary-precision ``numeric``. Carried values are read and
written back unexamined.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

import asyncpg

# Pinned on every connection the run opens, before any aggregate runs. The
# source-to-staging parity check compares strings produced by two different
# sessions on two different databases, and a timestamptz rendered as text under
# TimeZone='UTC' and under 'Asia/Tokyo' gives different md5s for the same
# instant.
SESSION_GUCS: dict[str, str] = {
    "TimeZone": "UTC",
    "DateStyle": "ISO, MDY",
    "extra_float_digits": "3",
    "bytea_output": "hex",
}

FORBIDDEN_SOURCE_DATABASE = "darkmem"

DEFAULT_IDLE_IN_TRANSACTION_TIMEOUT_MS = 900_000


class CutoverError(RuntimeError):
    """A refusal or an abort. Always names what went wrong and which rows."""


@dataclass(frozen=True)
class DsnIdentity:
    host: str
    port: int
    database: str

    def __str__(self) -> str:
        return f"{self.host}:{self.port}/{self.database}"


def normalise_dsn(dsn: str) -> str:
    """Strip SQLAlchemy's driver suffix so asyncpg accepts the DSN directly."""
    scheme, _, rest = dsn.partition("://")
    if not rest:
        raise CutoverError(f"not a DSN: {dsn!r}")
    base = scheme.split("+", 1)[0]
    if base not in {"postgres", "postgresql"}:
        raise CutoverError(f"unsupported DSN scheme {scheme!r}")
    return f"postgresql://{rest}"


def dsn_identity(dsn: str) -> DsnIdentity:
    parts = urlsplit(normalise_dsn(dsn))
    database = unquote(parts.path.lstrip("/"))
    if not database:
        raise CutoverError(f"DSN names no database: {dsn!r}")
    return DsnIdentity(
        host=(parts.hostname or "localhost").lower(),
        port=parts.port or 5432,
        database=database,
    )


def assert_distinct_databases(source_dsn: str, target_dsn: str) -> None:
    source = dsn_identity(source_dsn)
    target = dsn_identity(target_dsn)
    if source == target:
        raise CutoverError(
            f"source and target resolve to the same database ({source}); "
            "the transform would read and write the same rows"
        )


def assert_source_not_production(source_dsn: str) -> None:
    source = dsn_identity(source_dsn)
    if source.database == FORBIDDEN_SOURCE_DATABASE:
        raise CutoverError(
            f"refusing to open {FORBIDDEN_SOURCE_DATABASE!r} as the source. "
            "The transform reads a restored copy, never production"
        )


async def connect_source(dsn: str) -> asyncpg.Connection:
    """Open the source read-only at the database, not by convention.

    ``default_transaction_read_only`` makes an attempted write fail in Postgres
    rather than in code review.
    """
    assert_source_not_production(dsn)
    return await asyncpg.connect(
        normalise_dsn(dsn),
        server_settings={**SESSION_GUCS, "default_transaction_read_only": "on"},
    )


async def connect_target(
    dsn: str, idle_timeout_ms: int = DEFAULT_IDLE_IN_TRANSACTION_TIMEOUT_MS
) -> asyncpg.Connection:
    return await asyncpg.connect(
        normalise_dsn(dsn),
        server_settings={
            **SESSION_GUCS,
            "idle_in_transaction_session_timeout": str(idle_timeout_ms),
        },
    )


async def live_identity(conn: asyncpg.Connection) -> tuple[str, str, int]:
    row = await conn.fetchrow(
        "SELECT current_database() AS db, "
        "COALESCE(inet_server_addr()::text, 'local') AS addr, "
        "COALESCE(inet_server_port(), 0) AS port"
    )
    return row["db"], row["addr"], row["port"]


async def assert_distinct_live_databases(
    source: asyncpg.Connection, target: asyncpg.Connection
) -> None:
    """Catch a same-database pair the DSN comparison cannot see.

    Two DSNs can spell the same database differently — ``localhost`` against
    ``127.0.0.1``, a default port left implicit — so the identity is compared
    again once both connections are open.
    """
    if await live_identity(source) == await live_identity(target):
        db, addr, port = await live_identity(source)
        raise CutoverError(
            f"source and target are the same live database ({addr}:{port}/{db})"
        )

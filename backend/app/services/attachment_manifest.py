"""The attachment set's change gate (spec §3).

One SQL scalar, computed by Postgres, so `scripts/backup.sh` and `backup_ship`
cannot disagree about ordering, formatting or encoding: the shell producer runs
the same literal through `psql -At` and gets the same 64 hex characters this
returns. Aggregating client-side would put an ordering and a newline convention
in two places, and the two producers would drift the first time one changed.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

#: An attachment's bytes never change after `os.replace` -- the id is the
#: filename and there is no update path -- so the (id, sha256) set changes if
#: and only if a row was added or deleted. A bare count would miss a delete
#: plus an add inside one interval.
MANIFEST_SQL = (
    "SELECT encode(sha256(convert_to(coalesce(string_agg(id::text || ':' || "
    "sha256, E'\\n' ORDER BY id), ''), 'UTF8')), 'hex') FROM page_attachments"
)

#: The completion check's other half: a non-zero row count against an archive
#: holding no members is a mis-mounted volume, not an empty corpus.
COUNT_SQL = "SELECT count(*) FROM page_attachments"


async def manifest_hash(session: AsyncSession) -> str:
    """The 64-hex manifest of the whole attachment set.

    An empty table hashes the empty string rather than returning NULL, so a
    corpus with no attachments still has a stable value to compare against.
    """
    return (await session.execute(text(MANIFEST_SQL))).scalar_one()


async def attachment_count(session: AsyncSession) -> int:
    return int((await session.execute(text(COUNT_SQL))).scalar_one())

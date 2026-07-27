"""The labels a row of memory-derived data carries to describe its own scope.

A read that is deliberately wide — every project by ratified default, or a
deployment-wide operational queue — is honest only when its rows say which
project and lifecycle state they came from. Without them a consumer cannot
tell a foreign or superseded row from a local live one, which is the half of
the isolation bar that counts *unlabelled* escapes rather than wrongly
returned ones.

The vocabulary lives here once, and every producer stamps it at the point the
rows are made rather than at each call site: the list of consumers of these
channels has been wrong repeatedly, so a per-call-site fix leaves whichever
caller nobody enumerated unlabelled.
"""

from __future__ import annotations

from collections.abc import Mapping

SCOPE_LABEL_FIELDS: tuple[str, ...] = ("project", "status")

# The same two labels as SQL, for a raw-SQL producer joined to ``memories AS
# m``. ``memories.status`` is a Postgres enum, so the cast is what makes it
# arrive as a plain JSON string.
SCOPE_LABEL_COLUMNS = "m.project AS project, m.status::text AS status"

# The join that produces them off an embedding partition aliased ``e``. It is
# unconditional even when nothing is being scoped: the FK from every partition
# to ``memories`` makes it lossless, so labelling costs no row.
SCOPE_LABEL_JOIN = "JOIN memories m ON m.id = e.memory_id"


def scope_labels(source) -> dict:
    """The scope labels of a ``Memory`` row, a SQL result row, or a labelled dict.

    Deliberately strict: a producer that has not got both labels raises here
    instead of emitting ``None`` for one, which would read downstream as a row
    that genuinely has no project.
    """
    if isinstance(source, Mapping):
        return {name: source[name] for name in SCOPE_LABEL_FIELDS}
    return {name: getattr(source, name) for name in SCOPE_LABEL_FIELDS}

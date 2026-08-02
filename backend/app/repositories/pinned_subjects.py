"""Per-project pinned/dismissed subject lists — `projects.properties` jsonb
(doc 09 §3.4, doc 04 §7) — T2.20.

**Why this is not `project_registry.py`.** That module is read-only by
explicit design (its own docstring: "Adding a writer here without deciding
who owns project creation would put three surfaces back to improvising a
project registry"). This module adds no project-creation path and claims no
general write access to `properties` — it owns exactly the two keys doc 09
§3.4 assigns to the pin-suggestion flow, `pinned_subjects` and
`dismissed_subjects`, and touches nothing else in the jsonb blob.

**No schema change.** `projects (name, display_name, properties, created_at)`
already exists in the baseline (doc 04 §7); this is a new caller of an
existing column, not a new table or column.

**Why an upsert, not a plain UPDATE.** `project_registry.register` lazily
creates a project row on capture, so by the time a pin suggestion exists the
row should already be there. The upsert defends the gap case (a project
whose only rows come from a test fixture, a backfill order, or a race)
without adding a hard dependency on capture having run first.

**Idempotent by construction.** The jsonb `?` operator tests whether a string
is an element of a top-level array, so a repeated accept or dismiss of the
same subject appends nothing a second time — re-running the same decision is
a no-op, not a growing list.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

PINNED_KEY = "pinned_subjects"
DISMISSED_KEY = "dismissed_subjects"

_GET_LISTS = text(
    "SELECT COALESCE(properties -> 'pinned_subjects', '[]'::jsonb) AS pinned, "
    "COALESCE(properties -> 'dismissed_subjects', '[]'::jsonb) AS dismissed "
    "FROM projects WHERE name = CAST(:project AS text)"
)

_APPEND_SUBJECT = text(
    """
    INSERT INTO projects (name, properties)
    VALUES (
        CAST(:project AS text),
        jsonb_build_object(CAST(:list_key AS text), jsonb_build_array(CAST(:subject_key AS text)))
    )
    ON CONFLICT (name) DO UPDATE SET properties =
        CASE WHEN COALESCE(projects.properties -> CAST(:list_key AS text), '[]'::jsonb)
                  ? CAST(:subject_key AS text)
             THEN projects.properties
             ELSE jsonb_set(
                    projects.properties,
                    ARRAY[CAST(:list_key AS text)],
                    COALESCE(projects.properties -> CAST(:list_key AS text), '[]'::jsonb)
                        || to_jsonb(CAST(:subject_key AS text)),
                    true
                  )
        END
    """
)


async def get_subject_lists(
    session: AsyncSession, project: str
) -> tuple[set[str], set[str]]:
    """`(pinned_subject_keys, dismissed_subject_keys)` for `project`.

    An unregistered project reads as two empty sets rather than raising —
    "nothing pinned or dismissed yet" is the correct answer for a project
    with no `projects` row at all.
    """
    row = (await session.execute(_GET_LISTS, {"project": project})).mappings().first()
    if row is None:
        return set(), set()
    return set(row["pinned"] or []), set(row["dismissed"] or [])


async def append_subject(
    session: AsyncSession, project: str, list_key: str, subject_key: str
) -> None:
    """Add `subject_key` to `list_key` (`PINNED_KEY` or `DISMISSED_KEY`) for
    `project`, creating the `projects` row if it does not exist yet."""
    await session.execute(
        _APPEND_SUBJECT,
        {"project": project, "list_key": list_key, "subject_key": subject_key},
    )

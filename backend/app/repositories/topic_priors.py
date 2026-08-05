"""The durable per-project topic prior — `projects.properties` jsonb
(doc 09 §3.4) — T2.91.

**Why a durable store exists at all.** `memory_communities` is
delete-and-rewritten per project on every detection run (doc 06 §7), so the
only pre-rewrite state that ever existed lived in memory inside the
detection job's body, mid-run, and was discarded when the run ended. A read
door therefore had nothing to diff against and every topic read `new`
forever — `grown`, `stable` and `decayed` were unreachable on the wire. What
survives a rewrite has to be written down somewhere the rewrite does not
touch.

**Why here rather than a table.** `pinned_subjects.py` already established
the pattern doc 09 §3.4 assigns to this flow: a narrowly-scoped new writer
of `projects.properties`, no schema change, no claim on the rest of the
blob. This module owns exactly one more key, `topic_prior`, and touches
nothing else. A dedicated table would be the alternative and buys nothing
here — the prior is one small document per project, read whole and written
whole, never joined and never queried by shape.

**Why the whole document is replaced, not merged.** A prior is a complete
census of one run: a label missing from it means "that label did not exist
at capture time", which is precisely what makes `decayed` derivable. Merging
a new capture into an old one would resurrect labels that have been gone for
several runs and report them decaying over and over.

**Keyed on label, never on community id** (doc 06 §7, and T2.20's identity
rule). Ids churn on every run by construction, so a prior keyed on them
would match nothing; the deterministic dominant-entity label is the only
identity that survives, and it is the one `diff_topics` already classifies
on.
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TOPIC_PRIOR_KEY = "topic_prior"

_GET_PRIOR = text(
    "SELECT COALESCE(properties -> 'topic_prior', '{}'::jsonb) AS prior "
    "FROM projects WHERE name = CAST(:project AS text)"
)

# Same upsert shape, and the same reason, as `pinned_subjects.append_subject`:
# `project_registry.register` creates the row lazily on capture, so it should
# already exist by the time a detection run has anything to snapshot — but a
# project whose rows arrived by fixture or backfill must not lose its prior.
_SET_PRIOR = text(
    """
    INSERT INTO projects (name, properties)
    VALUES (
        CAST(:project AS text),
        jsonb_build_object('topic_prior', CAST(:prior AS jsonb))
    )
    ON CONFLICT (name) DO UPDATE SET properties = jsonb_set(
        projects.properties,
        ARRAY['topic_prior'],
        CAST(:prior AS jsonb),
        true
    )
    """
)


async def get_topic_prior(session: AsyncSession, project: str) -> dict[str, dict]:
    """The last captured census for `project`, `label -> fields`.

    An unregistered project, or one whose first detection run has not
    happened yet, reads as `{}` rather than raising — "there is no prior"
    is the correct answer, and it is the one that makes every label `new`.
    """
    row = (await session.execute(_GET_PRIOR, {"project": project})).mappings().first()
    if row is None:
        return {}
    return dict(row["prior"] or {})


async def set_topic_prior(
    session: AsyncSession, project: str, prior: dict[str, dict]
) -> None:
    """Replace `project`'s prior wholesale, creating the `projects` row if it
    does not exist yet."""
    await session.execute(
        _SET_PRIOR,
        {"project": project, "prior": json.dumps(prior, default=str)},
    )

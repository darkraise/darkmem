"""What was pushed, where, and under which budget (doc 13 §6.5) — T3.12.

Doc 01's F10 promise is context *before* the first prompt; the obligation that
comes with it is that the human can always see what the agent was told. An
injection the human cannot inspect is the silent context swap invariant 14
forbids, so every push journals — and the journal, not the managed block, is
the durable record: the block is overwritten on the next refresh, while
``events`` is append-only.

**Ids and counts, never the injected text.** Write-time minimization is the
standing rule (CLAUDE.md, events journal), and it binds hardest here: an inject
payload copying the content would duplicate every injected memory and fact into
a table that outlives their deletion, on every session start of every client.
The ids are enough to answer "what was I told" by joining to the rows that
still exist, and honest about the rows that no longer do.

**Two event types, one writer.** ``inject`` records a push; ``inject_curbed``
records the human turning it off — doc 15 §3.2's *Curbed* state, where the
block is cleared to an empty marker pair. Both landed in the closed vocabulary
taxonomy-first, long before this emitter; this module is what makes them live,
which is why it is also what owes them a place in the frontend's map.

**No producer yet, deliberately.** T3.10 owns the content fill and is held by
G-D, so nothing calls this in the tree today. It ships as the primitive its
caller will need, the way T2.08's placeholders and T0.13's inert partitions
did (invariant 23) — with the difference that this one is fully functional the
moment a caller exists.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.events import record_event

logger = logging.getLogger(__name__)

__all__ = [
    "INJECT_CURBED_EVENT",
    "INJECT_EVENT",
    "OBJECT_TYPE",
    "record_inject",
    "record_inject_curbed",
]

INJECT_EVENT = "inject"
INJECT_CURBED_EVENT = "inject_curbed"

# The push targets a *tool's context file*, not a memory or a fact, and the
# vocabulary has no object type for a file. `system` is the honest choice: the
# event is about this installation's own behaviour rather than about any vault
# row, and inventing an object type for it would put a new value in a closed
# taxonomy to describe something none of the readers key on.
OBJECT_TYPE = "system"


def _ids(values) -> list[str]:
    """Ids as strings, order preserved.

    Order is the *served* order, which is the point: doc 15 §3.4's fill is
    truth-first, so the sequence records the priority the budget actually
    spent, not merely the set it reached. Sorting here would erase that.
    """
    return [str(value) for value in (values or [])]


async def record_inject(
    session: AsyncSession,
    *,
    tool: str,
    context_file: str,
    memory_ids=None,
    fact_ids=None,
    article_ids=None,
    budget_tokens: int | None = None,
    tokens_used: int | None = None,
    project: str = "default",
    actor: str | None = None,
) -> bool:
    """Journal one push, returning whether the row landed. Does not commit.

    The return is not decoration. For this module the journal **is** the
    deliverable — doc 13 §6.5's whole point is that the human can see what the
    agent was told — so a caller that pushed context while the record silently
    failed has done the thing invariant 14 forbids. It does not raise, because
    T2.113's strict contract belongs to the verification ladder where a lost
    row corrupts a measurement; here the caller (T3.10) decides whether to
    surface it, and it can only decide if it is told.

    The three id lists stay separate rather than merging into one: a reader
    asking "was a fact injected as corroborated" needs to know which ids are
    facts, and a merged list would make the layer unrecoverable without
    querying every table for each id.

    ``budget_tokens`` and ``tokens_used`` are both recorded, and the pair is
    what makes the record diagnostic rather than decorative — a push that used
    40 of 4000 tokens and a push that hit its ceiling look identical from the
    id list alone, and they mean different things about what the agent was not
    told.
    """
    return await record_event(
        session,
        event_type=INJECT_EVENT,
        object_type=OBJECT_TYPE,
        object_id=None,
        project=project,
        actor=actor,
        payload={
            "tool": tool,
            "context_file": context_file,
            "memory_ids": _ids(memory_ids),
            "fact_ids": _ids(fact_ids),
            "article_ids": _ids(article_ids),
            "budget_tokens": budget_tokens,
            "tokens_used": tokens_used,
        },
    )


async def record_inject_curbed(
    session: AsyncSession,
    *,
    tool: str,
    context_file: str,
    project: str = "default",
    actor: str | None = None,
    reason: str | None = None,
) -> bool:
    """Journal the curb, returning whether the row landed (doc 15 §3.2).

    A separate event type rather than an ``inject`` with an empty id list: the
    two are different facts, and a reader counting injections would otherwise
    count a curb as a push of nothing. It also means the timeline shows *when*
    the human turned it off, which is the question a curb is asked about.
    """
    return await record_event(
        session,
        event_type=INJECT_CURBED_EVENT,
        object_type=OBJECT_TYPE,
        object_id=None,
        project=project,
        actor=actor,
        payload={"tool": tool, "context_file": context_file, "reason": reason},
    )


def injected_ids(payload: dict) -> list[UUID | str]:
    """Every id one inject payload names, in served order.

    A reader helper rather than a stored field: the three lists are the record,
    and a stored flat copy would be a second answer to the same question that
    could disagree with the first.
    """
    out: list[UUID | str] = []
    # Doc 15 §3.4's fill order is **facts, then articles, then memory
    # summaries** — truth-first. The first version iterated memories first and
    # called the result "served order", which inverted the very ordering the
    # docstring claimed to preserve.
    for key in ("fact_ids", "article_ids", "memory_ids"):
        out.extend(payload.get(key) or [])
    return out

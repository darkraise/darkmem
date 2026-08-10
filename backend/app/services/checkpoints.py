"""Session checkpoints — the store half (spec §Feature-2, T3.16).

A checkpoint is one agent run's note to its successor: a compact ``summary``
and a structured ``next_steps`` list, keyed on the ``origin_key`` capture
already stamps for that run (T1.11). T3.17 turns the latest one into a
budgeted resume block; this module only stores and fetches.

**One writer for both doors.** REST and MCP are two transports over this
module, never two implementations — invariant 17 is two-door parity, and the
way parity survives a later change is that there is only one behaviour to
change. ``tests/test_door_parity.py`` asserts it from the outside; this
module's single-writer shape is what makes the assertion cheap to keep true.

**Bounds are enforced here and in the database, deliberately twice.** The
schema layer refuses an oversized payload with a 422 a caller can act on; the
CHECK constraints refuse it whatever route reached the table. Neither is
redundant: the first is the good error message, the second is the guarantee.

**No verification status, and no route into the vault.** A checkpoint is what
an agent said about its own run — nothing corroborated it, so it carries no
rung, and it is not a memory. T3.18 owns that rule as an invariant; the
absence of any capture call in this module is what implements it today.

**The key is resolved through doc 05 §2.1, and an undeclared one is refused
rather than merged.** Both halves matter and they pull in opposite directions
from the memory side. Resolving is what the plan asked for (feature-epics F10
keys checkpoints on "the agent-run identity, doc 05 §2.1") and it is what
makes correlation possible at all: the client declares the same raw identity
and the same client name to both doors, and the server derives the same key on
each. The derivation is shared *and* each door must feed it the source its own
transport declares — a door passing a constant would put its checkpoints in a
key space the other door cannot read, which is what the MCP door did until
2026-08-10.

**Unlike capture, this surface does echo the resolved key.** ``serialize``
returns ``origin_key`` and ``CheckpointResponse`` serves it on both verbs of
both doors. CLAUDE.md's "no response echoes it" is a property of the *capture*
doors, where the key is a corroboration-counting key and observing another
run's is the hazard; here it is a lookup key and a caller can only ever be
handed back the row it looked up under its own declared identity. This
docstring claimed the capture property for two commits after the doors started
resolving, which would have mis-triaged anyone auditing
corroboration-independence across doors; corrected 2026-08-10.

But :func:`resolve_origin_key`'s *fallback* must not be inherited. That
function merges an undeclared origin to a coarse `unknown:<source>:<project>`
bucket, and its own docstring gives the reason: for corroboration
"undercounting only delays a promotion; overcounting manufactures one", so
merging is the safe direction **because the key is a counting key**. Here it
is a **lookup** key, and the same merge is unsafe: two concurrent runs that
declared nothing would share one bucket, and each `latest_checkpoint` would
return whichever saved last — T3.17's resume silently loading another run's
notes, a wrong-context failure with no symptom. So an undeclared origin is
refused at the door instead.

**What the correlation actually guarantees, stated because the first version
overstated it.** A checkpoint and the memories of one run share a key *when
the client declares the same identity and the same source to both doors*. It
is a client-discipline property, not a system guarantee and not a join: a run
capturing over MCP and checkpointing over REST resolves two different sources
and therefore two different keys. Nothing here enforces it and nothing can.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mcp.client_identity import UNKNOWN_ORIGIN_PREFIX, resolve_origin_key
from app.models.checkpoint import SessionCheckpoint
from app.services.events import record_event

__all__ = [
    "CHECKPOINT_SAVED_EVENT",
    "DOOR_SOURCE",
    "UndeclaredOrigin",
    "resolve_checkpoint_origin",
    "MAX_NEXT_STEPS",
    "MAX_STEP_LENGTH",
    "MAX_SUMMARY_LENGTH",
    "latest_checkpoint",
    "save_checkpoint",
]

CHECKPOINT_SAVED_EVENT = "checkpoint_saved"
OBJECT_TYPE = "checkpoint"

# The source a checkpoint door assumes when the client names none. It is the
# *fallback*, not a constant: `resolve_client_source` prefers the
# X-Darkmem-Client header and then the User-Agent product map, so a client
# that names itself to the capture door the same way lands on the same source
# here -- which is the half of the correlation this module can influence.
#
# It is the fallback on *both* doors, which is a property of the call sites
# rather than of this constant, and the MCP door shipped passing it as a
# constant while this comment said otherwise. The behavioural pin is
# `test_one_declared_client_lands_on_one_key_through_either_door`; a comment
# cannot hold this on its own.
DOOR_SOURCE = "checkpoint"

# The bounds the done-when asks for. Mirrored by CHECK constraints in the
# baseline; these produce the 422, those produce the guarantee.
MAX_SUMMARY_LENGTH = 4000
MAX_NEXT_STEPS = 50
MAX_STEP_LENGTH = 500

# The database bounds `next_steps` with `pg_column_size(...) <= NEXT_STEPS_MAX_BYTES`.
# The schema layer must refuse everything the constraint would, or the API
# accepts a payload its own validation called valid and the write dies at
# flush as a 500. The two limits were born different -- 50x500 *characters*
# against 16384 *bytes* -- so 15 steps of 500 CJK characters passed Pydantic
# and violated the CHECK. Both sides now read this one number, and the schema
# checks encoded size rather than character count.
NEXT_STEPS_MAX_BYTES = 16384


class UndeclaredOrigin(ValueError):
    """A checkpoint arrived with no declared agent-run identity.

    Refused rather than merged into :func:`resolve_origin_key`'s coarse
    fallback. See the module docstring: that bucket is safe for counting and
    unsafe for lookup, because two undeclared runs would share it and each
    would read the other's checkpoint as its own.
    """


def resolve_checkpoint_origin(declared, *, source: str, project: str) -> str:
    """The run's key, by doc 05 §2.1's derivation, or a refusal.

    Deliberately calls the same resolver capture calls rather than formatting
    `source:id` here: the sanitisation, the length bound and the prefix are
    that function's, and a second copy of them is a second answer to one
    question -- which is how the two RRF constants drifted.
    """
    if not isinstance(declared, str) or not declared.strip():
        raise UndeclaredOrigin(
            "a checkpoint needs a declared agent-run identity: send "
            "`origin_key`, or the X-Darkmem-Origin header the client mints at "
            "process boot. Undeclared checkpoints cannot be merged into one "
            "bucket the way undeclared captures can -- two runs sharing it "
            "would each read the other's checkpoint as their own."
        )
    resolved = resolve_origin_key(declared, None, source=source, project=project)
    if resolved.startswith(f"{UNKNOWN_ORIGIN_PREFIX}:"):
        # Unreachable while `declared` is non-empty -- the resolver only falls
        # back when it finds nothing -- but asserted rather than assumed,
        # because the failure it guards is silent and lands in T3.17.
        raise UndeclaredOrigin(
            f"origin resolution produced the merge-to-one bucket {resolved!r}; "
            "refusing to store a checkpoint under a key shared by every "
            "unattributed run of this source and project"
        )
    if resolved == f"{source}:":
        # The refusal above was reachable round the front: `_sanitize_origin`
        # drops separators and unprintables, so ":::", a lone zero-width space
        # and " : " each reduce to the empty string and land on the bare
        # "<source>:" -- one key shared by every run that declares such a
        # string. Not the resolver's fallback bucket, but the same hazard, and
        # the guard above cannot see it because the prefix is wrong. Keyed on
        # the *sanitised* result rather than on the raw string containing a
        # stripped character, since "boot:1" sanitises to "boot1" and is a
        # perfectly good identity.
        raise UndeclaredOrigin(
            f"the declared agent-run identity {declared!r} contains nothing "
            f"that survives sanitisation, so it resolves to the bare "
            f"{resolved!r} -- a key every such run would share, and each would "
            "read the others' checkpoints as its own. Send an identity with at "
            "least one printable, non-separator character."
        )
    return resolved


async def save_checkpoint(
    session: AsyncSession,
    *,
    origin_key: str,
    summary: str,
    next_steps: list[str] | None = None,
    project: str = "default",
    actor: str | None = None,
) -> SessionCheckpoint:
    """Store one checkpoint and journal it. Does not commit.

    Append-only by design: a run that saves twice keeps both rows, and
    ``latest_checkpoint`` reads the newer. Overwriting in place would make the
    checkpoint stream unreconstructable — a resume that loaded the wrong note
    could not be explained afterwards — and the row is small enough that
    keeping the history costs nothing worth the loss.

    The journal row is best-effort, unlike a verification transition: no metric
    is SQL over these events, so a checkpoint that saved but did not journal is
    a lost log line rather than a corrupted denominator. ``record_event``'s
    ordinary never-raises contract is therefore the right one here, and the
    return is deliberately ignored (see CLAUDE.md's events section for the four
    callers where it is not).
    """
    row = SessionCheckpoint(
        id=uuid4(),
        origin_key=origin_key,
        project=project,
        summary=summary,
        next_steps=list(next_steps or []),
    )
    session.add(row)
    await session.flush()

    await record_event(
        session,
        event_type=CHECKPOINT_SAVED_EVENT,
        object_type=OBJECT_TYPE,
        object_id=row.id,
        project=project,
        actor=actor,
        # The summary is not copied into the payload. Write-time minimization
        # is the standing rule (CLAUDE.md, events journal): the row itself
        # holds the text, the journal needs only that a checkpoint happened
        # and how big it was, and an event payload outlives deletion of what
        # it describes.
        payload={"origin_key": origin_key, "next_steps": len(row.next_steps)},
    )
    return row


async def latest_checkpoint(
    session: AsyncSession, *, origin_key: str, project: str = "default"
) -> SessionCheckpoint | None:
    """The newest checkpoint for one agent run, or ``None``.

    One indexed query, which is the done-when: ``ix_session_checkpoints_latest``
    is ``(project, origin_key, created_at DESC, id DESC)``, so this is a
    one-row index scan and not a sort over the run's history. The ``id``
    tie-break is not decoration — two checkpoints saved inside one transaction
    share ``now()``, and without it "latest" would be whichever the planner
    happened to return.
    """
    statement = (
        select(SessionCheckpoint)
        .where(
            SessionCheckpoint.project == project,
            SessionCheckpoint.origin_key == origin_key,
        )
        .order_by(
            SessionCheckpoint.created_at.desc(),
            SessionCheckpoint.id.desc(),
        )
        .limit(1)
    )
    return (await session.execute(statement)).scalar_one_or_none()


def serialize(row: SessionCheckpoint) -> dict[str, Any]:
    """The wire shape both doors serve, so they cannot drift into two."""
    return {
        "id": str(row.id),
        "origin_key": row.origin_key,
        "project": row.project,
        "summary": row.summary,
        "next_steps": list(row.next_steps or []),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }

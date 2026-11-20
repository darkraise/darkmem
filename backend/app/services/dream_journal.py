"""The dreaming pass's journal vocabulary, owned by neither end of it.

The consolidation pass writes a uniform ``consolidated`` event per action; the
digest reads that stream and the undo service inverts it. All three need the
same event type, the same three action names, the same pass key under
``properties.dream`` and the same metadata marker paths, and a literal
duplicated across a producer and a consumer is exactly the drift this corpus
keeps finding (``code_query.py``'s private ``RRF_K`` was the standing example,
and closing it took a build-failing scan rather than a reading).

**This module exists because the consumer cannot import the producer.**
Invariant 15's source scan derives its forbidden module set from
``dream_jobs.py``'s own imports and applies it to every file under ``app/``, so
no non-family module may name the dreaming pass's module in any spelling — not
even to read one constant. The derivation is deliberately ONE HOP (T2.67
documents that as a contract), so a neutral module the pass imports but the
umbrella does not stays outside the set and both ends may share it.

Everything here is a constant or a pure function over a ``metadata`` mapping,
apart from the two state-row helpers at the bottom, so the digest's advisory
read and the undo door's authoritative one cannot answer differently.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config

# ── the journal stream ───────────────────────────────────────────────────

EVENT_TYPE = "consolidated"
OBJECT_TYPE = "memory"
DETECTOR = "dedup"

# The undo's own event type. An undo is an action, not an erasure: it appends a
# row against the same object, so one memory's timeline carries the action and
# its reversal in order.
UNDONE_EVENT_TYPE = "undone"

ACTION_SUBSUME = "subsume"
ACTION_ASSOCIATE = "associate"
ACTION_REFINE = "refine"

ACTIONS: frozenset[str] = frozenset({ACTION_SUBSUME, ACTION_ASSOCIATE, ACTION_REFINE})

# ── the state each action keys itself under ──────────────────────────────

# The dedup pass's own key under `memory_relations.properties.dream`. Keyed by
# pass name so a sibling derivation pass can coexist on the one row the UNIQUE
# forces them to share.
NEAR_DUPLICATE_PASS = "near_duplicate"

# T2.16's key, and the reason the pass-keyed layout exists at all. Two passes
# may legitimately propose the same ``(source, target, rel_type)`` triple for
# different reasons; sharing one key would make each pass's strip erase the
# other's state on the single row the UNIQUE forces them onto.
DERIVATION_PASS = "associative_derivation"


def associate_pass_key(payload: dict | None) -> str:
    """Which pass's block an ``associate`` action wrote.

    Defaults to the near-duplicate pass because rows journalled before T2.16
    carry no ``pass_key`` and were all written by that arm. Read by the undo
    door's inverse *and* by its compare-and-swap: a hardcoded key there would
    restore or clear the wrong pass's block while reporting success.
    """
    key = (payload or {}).get("pass_key")
    return key if isinstance(key, str) and key else NEAR_DUPLICATE_PASS

HYGIENE_STATE_OPEN = "open"

REFINE_MARKER_PATH = ("dream", "refine")

# The suppression tombstone an undone subsumption leaves behind, keyed by the
# counterpart memory id so one memory can carry tombstones against several
# partners with no list-mutation semantics and the read stays a dict lookup.
SUBSUME_TOMBSTONE_KEY = "undone_subsume"
SUBSUME_TOMBSTONE_PATH = ("dream", SUBSUME_TOMBSTONE_KEY)


def content_sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _node_at(metadata: dict | None, path: tuple[str, ...]) -> dict | None:
    node = metadata if isinstance(metadata, dict) else {}
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            return None
    return node if isinstance(node, dict) else None


def refine_marker_of(metadata: dict | None) -> dict | None:
    return _node_at(metadata, REFINE_MARKER_PATH)


def subsume_tombstone_of(
    metadata: dict | None, counterpart_id: str
) -> dict | None:
    return _node_at(metadata, (*SUBSUME_TOMBSTONE_PATH, str(counterpart_id)))


def subsume_tombstone_blocks(older, newer) -> bool:
    """Whether a human's undo suppresses re-proposing this ordered pair.

    A *nomination* filter, read where candidate pairs are generated — the same
    shape ``needs_refine`` already has for the refine work set. Nothing in the
    status lifecycle consults it: the supersession primitive will still retire
    this exact pair for any caller that asks.

    Keyed on **both** contents, because the human's judgement was about these
    two texts. Once either side's content genuinely changes the judgement is
    stale and the pass may re-ask — the same principle as the refine marker,
    and the reason the tombstone records a counterpart sha it could not
    otherwise derive from the subsume payload.
    """
    tombstone = subsume_tombstone_of(older.metadata, newer.memory_id)
    if tombstone is None:
        return False
    return (
        tombstone.get("content_sha") == older.content_sha
        and tombstone.get("counterpart_content_sha") == newer.content_sha
    )


# ── the memory row every action locks ────────────────────────────────────

# `tag_names` rides the read so a compare-and-swap sees the tags as of the
# lock, not as of a render some minutes earlier. The digest reads the identical
# projection without the lock, so its advisory answer is computed from the same
# inputs as the undo door's.
_MEMORY_STATE_SQL = """
    SELECT m.status::text AS status,
           m.content,
           m.project,
           m.summary,
           m.metadata,
           CAST(m.superseded_by AS text) AS superseded_by,
           COALESCE(
               ARRAY(
                   SELECT t.name FROM memory_tags mt
                   JOIN tags t ON t.id = mt.tag_id
                   WHERE mt.memory_id = m.id
                   ORDER BY t.name
               ),
               CAST(ARRAY[] AS text[])
           ) AS tag_names
    FROM memories m
    WHERE m.id = CAST(:memory_id AS uuid)
"""

LOCK_MEMORY_STATE = text(f"{_MEMORY_STATE_SQL}    FOR UPDATE")
READ_MEMORY_STATE = text(_MEMORY_STATE_SQL)


# ── a pass's own bookkeeping row ─────────────────────────────────────────

# Rotation state lives in its own `config` row, never in the job's config
# dict: `JobRegistry.set_config` validates against the job's schema, so a
# cursor there would be rejected as an unknown key or become operator-editable.


async def read_state_row(session: AsyncSession, key: str) -> dict:
    row = (
        await session.execute(select(Config).where(Config.key == key))
    ).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return {}
    return dict(row.value)


async def write_state_row(session: AsyncSession, key: str, value: dict) -> None:
    row = (
        await session.execute(select(Config).where(Config.key == key))
    ).scalar_one_or_none()
    if row is None:
        session.add(Config(key=key, value=value))
    else:
        row.value = value

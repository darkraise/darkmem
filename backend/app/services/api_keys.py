"""The programmatic bearer credential — mint, parse, verify (doc 18 §5).

A credential is ``dmk_<key_id>_<secret>``. ``key_id`` is a public lookup handle
and ``secret`` is the part that authenticates; only a bcrypt hash of the secret
is stored, and the plaintext exists exactly once, in the response to the call
that minted it.

**Why the shape carries a public id at all.** bcrypt salts per row, so hashing a
presented secret does not reproduce the stored hash of that same secret — you
cannot look a key up by what the caller sent. Without a lookup handle the only
way to answer "is this a valid key" is to bcrypt-verify the presented secret
against every row, which is O(rows) key-stretching operations per request and a
denial-of-service surface in its own right. ``key_id`` turns that into one
indexed read and one verify. That is the whole reason `api_keys` gains a column.

**Constant time means the verify, not the parse.** The format is public
structure and leaks nothing by failing fast on a malformed string. The secret
comparison runs through ``bcrypt.checkpw``, whose digest compare is
constant-time. The channel that would remain is the *absence* of a row: a miss
that skipped the verify answers in microseconds where a hit pays the full
bcrypt cost, which tells a prober that a guessed ``key_id`` exists. So a miss
burns an equivalent verify against a fixed sentinel.

**The alphabet is lowercase RFC 4648 base32.** It excludes ``_``, so the two
delimiters are unambiguous and the credential parses by an exact three-way
split rather than a bounded one; it excludes the ``0``/``O`` and ``1``/``l``
homoglyphs, so a hand-copied key fails to parse rather than silently matching
nothing; and it is single-case, so a transport that folds case does not
invalidate a credential.

``last_used_at`` is bumped by :func:`mark_key_used`, which the scope
dependency calls after a credential authenticates — **not** by the
authentication routine itself, which also runs for calls that then fail a
scope check. The MCP door also marks every other authenticated request
(``tools/list``, ``initialize``), so the bump is throttled to once per
:data:`MARK_USED_INTERVAL` per key. This module previously deferred the bump to "T4.02's per-call
stamping"; T4.02 closed without it, leaving the column with zero writers while
the settings card rendered "never used" as a verdict, which is how an
operator would have failed to notice a leaked key in daily use (E4 epic
review, C1). The write goes through its own committed session for the reason
``auth.py``'s audit rows do: a request that raises must not roll back the
record that it happened.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.api_key import ApiKey
from app.services.api_key_scopes import parse_scopes, read_scopes
from app.services.events import (
    API_KEY_CREATED,
    API_KEY_REVOKED,
    record_event,
)

logger = logging.getLogger(__name__)


KEY_PREFIX = "dmk"
KEY_ID_LENGTH = 16
SECRET_LENGTH = 32

_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"
_ALPHABET_SET = frozenset(_ALPHABET)

# A bcrypt hash of the fixed, public string below. Not a credential: nothing
# authenticates against it. It exists so a lookup miss can pay the same
# key-stretching cost a hit pays, which is what keeps a probe from
# distinguishing a real key_id from an invented one by timing alone.
_ABSENT_SENTINEL = b"darkmem-api-key-absent-sentinel"
_ABSENT_SENTINEL_HASH = b"$2b$12$hUp/eRJucU6TA5QD2wH7Au8gwTNkdt3pPQUPhvJfdEg4hjCCj0glu"

# A key's ``last_used_at`` moves at most once per this window. It is a
# staleness signal read in minutes and days, and an agent's MCP session sends
# several requests a second, so an unthrottled bump would be a write per call.
MARK_USED_INTERVAL = timedelta(seconds=60)
# Per-process memo of the last bump, so a call inside the window costs no
# database round trip at all. The UPDATE's own predicate repeats the window,
# which keeps the throttle honest across a restart.
_last_marked: dict[uuid.UUID, datetime] = {}

# Verified credentials, keyed by sha256 of the presented token so no plaintext
# is held, mapped to (principal, expires_at, cached_at). In-process state: it
# relies on the single worker (invariant 13) and on restore-cycle.sh stopping
# the app before it swaps the database underneath it.
VERIFY_CACHE_SECONDS = 60.0
_verified: dict[str, tuple["KeyPrincipal", datetime | None, float]] = {}
_revoked_ids: set[uuid.UUID] = set()
_cache_clock = time.monotonic


@dataclass(frozen=True)
class MintedCredential:
    """A freshly minted credential, plaintext included exactly once.

    ``secret`` is excluded from the repr so an accidental log line or a
    traceback frame holding this object does not publish the one copy of the
    plaintext that will ever exist.
    """

    key_id: str
    secret: str = field(repr=False)

    @property
    def token(self) -> str:
        return f"{KEY_PREFIX}_{self.key_id}_{self.secret}"


@dataclass(frozen=True)
class KeyPrincipal:
    """An authenticated programmatic caller."""

    api_key_id: uuid.UUID
    name: str
    scopes: frozenset[str]


def mint_credential() -> MintedCredential:
    return MintedCredential(
        key_id="".join(secrets.choice(_ALPHABET) for _ in range(KEY_ID_LENGTH)),
        secret="".join(secrets.choice(_ALPHABET) for _ in range(SECRET_LENGTH)),
    )


def parse_credential(raw: object) -> tuple[str, str] | None:
    """Split a presented credential into ``(key_id, secret)``.

    Returns ``None`` for anything that is not exactly the documented shape.
    A malformed credential is simply not a credential — there is nothing to
    report that the 401 does not already say, and naming which part failed
    would tell a prober how far it got.
    """
    if not isinstance(raw, str):
        return None
    parts = raw.split("_")
    if len(parts) != 3:
        return None
    prefix, key_id, secret = parts
    if prefix != KEY_PREFIX:
        return None
    if len(key_id) != KEY_ID_LENGTH or len(secret) != SECRET_LENGTH:
        return None
    if not _ALPHABET_SET.issuperset(key_id):
        return None
    if not _ALPHABET_SET.issuperset(secret):
        return None
    return key_id, secret


def looks_like_credential(raw: object) -> bool:
    """Whether a bearer value claims to be an API key rather than a JWT.

    Used to route the ``Authorization`` header, which both credentials share.
    A claim, not a verdict: it decides which verifier runs, never whether the
    caller is admitted.
    """
    return isinstance(raw, str) and raw.startswith(f"{KEY_PREFIX}_")


def hash_secret(secret: str) -> str:
    return bcrypt.hashpw(secret.encode(), bcrypt.gensalt()).decode()


def _burn_equivalent_work() -> None:
    bcrypt.checkpw(_ABSENT_SENTINEL, _ABSENT_SENTINEL_HASH)


def verify_secret(secret: str, key_hash: str | None) -> bool:
    """Check a presented secret against a stored hash at a fixed cost.

    ``key_hash`` of ``None`` is the lookup-miss case and still pays a verify.
    An unusable stored hash denies rather than raising: a hand-edited row must
    cost its holder access, not turn every request into a 500.
    """
    if not key_hash:
        _burn_equivalent_work()
        return False
    try:
        return bcrypt.checkpw(secret.encode(), key_hash.encode())
    except ValueError:
        logger.warning("api_keys row carries an unusable hash; denying")
        _burn_equivalent_work()
        return False


async def authenticate(
    session: AsyncSession,
    raw: object,
    *,
    now: datetime | None = None,
) -> KeyPrincipal | None:
    """Resolve a presented credential, or ``None`` for every failure.

    The secret is verified *before* revocation and expiry are consulted, so
    holding a revoked key's id without its secret reveals nothing that holding
    an invented id does not: both answers cost one bcrypt and say ``None``.

    ``verify_secret`` runs bcrypt at the stored cost factor, which is
    synchronous CPU work worth roughly 167ms. With darkmem's single uvicorn
    worker (invariant 13) that would otherwise stall the event loop -- the
    whole process, not just this request -- for every call, including the
    sentinel burn on a lookup miss. It is offloaded to a worker thread via
    ``asyncio.to_thread`` so the loop stays free while it runs.

    The row is fetched and the fields this function needs are copied out to
    locals *before* the bcrypt call, and the session is committed right after
    the fetch -- releasing whatever the read was holding -- so the ~167ms in
    the thread pool does not also hold a pooled database connection idle.
    Nothing below the commit touches ``row`` or the session again.
    """
    parsed = parse_credential(raw)
    if parsed is None:
        return None
    key_id, secret = parsed
    moment = now or datetime.now(timezone.utc)

    digest = hashlib.sha256(raw.encode()).hexdigest()
    hit = _verified.get(digest)
    if hit is not None:
        principal, expires_at, cached_at = hit
        if principal.api_key_id in _revoked_ids:
            _verified.pop(digest, None)
            return None
        if expires_at is not None and expires_at <= moment:
            _verified.pop(digest, None)
            return None
        if _cache_clock() - cached_at < VERIFY_CACHE_SECONDS:
            return principal
        _verified.pop(digest, None)

    row = (
        await session.execute(select(ApiKey).where(ApiKey.key_id == key_id))
    ).scalar_one_or_none()

    if row is None:
        await session.commit()
        await asyncio.to_thread(verify_secret, secret, None)
        return None

    key_hash = row.key_hash
    row_id = row.id
    row_name = row.name
    row_scopes = row.scopes
    row_revoked_at = row.revoked_at
    row_expires_at = row.expires_at

    await session.commit()

    if not await asyncio.to_thread(verify_secret, secret, key_hash):
        return None

    if row_revoked_at is not None:
        return None
    if row_expires_at is not None and row_expires_at <= moment:
        return None

    principal = KeyPrincipal(
        api_key_id=row_id,
        name=row_name,
        scopes=read_scopes(row_scopes),
    )
    # A revoke that committed while this verify ran must not be undone by
    # caching the principal it read before the revoke.
    if row_id not in _revoked_ids:
        _verified[digest] = (principal, row_expires_at, _cache_clock())
    return principal


def forget_revoked_key(api_key_id: uuid.UUID) -> None:
    """Refuse a revoked key's cached entries; each is evicted on its next hit,
    which answers without a bcrypt verify."""
    _revoked_ids.add(api_key_id)


async def issue_key(
    session: AsyncSession,
    *,
    name: str,
    scopes: object,
    expires_at: datetime | None = None,
    actor: str | None = None,
) -> tuple[ApiKey, str]:
    """Mint a key. Returns the row and the plaintext credential, shown once.

    Raises ``ScopeRejected`` before anything is written, so a request naming an
    unknown scope leaves no row behind.
    """
    granted = parse_scopes(scopes)
    credential = mint_credential()

    row = ApiKey(
        name=name,
        key_id=credential.key_id,
        key_hash=hash_secret(credential.secret),
        scopes=list(granted),
        expires_at=expires_at,
    )
    session.add(row)
    await session.flush()

    # `api_key_id` stays null: this row records a human session minting a
    # credential, not a call made with one. `object_id` is what names the key.
    await record_event(
        session,
        event_type=API_KEY_CREATED,
        object_type="system",
        object_id=row.id,
        actor=actor,
        payload={"name": name, "scopes": list(granted)},
    )
    return row, credential.token


async def mark_key_used(
    api_key_id: uuid.UUID, *, now: datetime | None = None,
) -> None:
    """Record that this key just authenticated a call.

    Opens its own session and commits, so the bump survives a request that
    later raises — a probe against a nonexistent repository is exactly the
    traffic an operator most wants to see from a leaked key, and it is also
    the traffic whose request transaction never commits.

    Degrades loudly and never raises into the caller: a failed bump must not
    turn an authenticated request into a 500. The `events` row written beside
    it is the authoritative record; this column is the operator's index into
    it.

    Throttled: a key bumped less than :data:`MARK_USED_INTERVAL` ago is left
    alone, without opening a session when this process made that bump.
    """
    if settings.read_only:
        # Increment 7 group B: the bump would be refused by the viewer role on
        # every MCP call. Returning before the session is opened keeps a
        # read-only worker's log about the worker rather than about this.
        return

    stamp = now or datetime.now(timezone.utc)
    previous = _last_marked.get(api_key_id)
    if previous is not None and stamp - previous < MARK_USED_INTERVAL:
        return

    from app.database import async_session_factory  # noqa: PLC0415

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                update(ApiKey)
                .where(ApiKey.id == api_key_id)
                .where(or_(
                    ApiKey.last_used_at.is_(None),
                    ApiKey.last_used_at < stamp - MARK_USED_INTERVAL,
                ))
                .values(last_used_at=stamp)
            )
            await session.commit()
    except Exception:
        logger.warning("api_keys: could not bump last_used_at for %s", api_key_id, exc_info=True)
        return
    # Only a bump this process made starts its window: a row the predicate
    # skipped was stamped at a time this process does not know.
    if result.rowcount == 1:
        _last_marked[api_key_id] = stamp


async def revoke_key(
    session: AsyncSession,
    key_row_id: uuid.UUID,
    *,
    actor: str | None = None,
    now: datetime | None = None,
) -> bool:
    """Revoke a key in place. Returns False when there was nothing to revoke.

    The row is retained rather than deleted: `events.api_key_id` carries no
    foreign key, so deleting the row would leave every call that key ever made
    attributed to an id nothing explains.
    """
    row = (
        await session.execute(select(ApiKey).where(ApiKey.id == key_row_id))
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        return False

    row.revoked_at = now or datetime.now(timezone.utc)
    await session.flush()
    # Marked before the caller commits: a revoke that then rolls back leaves the
    # key uncached (bcrypt-verified on every call) in this process until restart.
    forget_revoked_key(row.id)
    await record_event(
        session,
        event_type=API_KEY_REVOKED,
        object_type="system",
        object_id=row.id,
        actor=actor,
        payload={"name": row.name},
    )
    return True

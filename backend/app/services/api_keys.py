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
scope check. This module previously deferred the bump to "T4.02's per-call
stamping"; T4.02 closed without it, leaving the column with zero writers while
the settings card rendered "never used" as a verdict, which is how an
operator would have failed to notice a leaked key in daily use (E4 epic
review, C1). The write goes through its own committed session for the reason
``auth.py``'s audit rows do: a request that raises must not roll back the
record that it happened.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
    """
    parsed = parse_credential(raw)
    if parsed is None:
        return None
    key_id, secret = parsed

    row = (
        await session.execute(select(ApiKey).where(ApiKey.key_id == key_id))
    ).scalar_one_or_none()

    if row is None:
        verify_secret(secret, None)
        return None
    if not verify_secret(secret, row.key_hash):
        return None

    moment = now or datetime.now(timezone.utc)
    if row.revoked_at is not None:
        return None
    if row.expires_at is not None and row.expires_at <= moment:
        return None

    return KeyPrincipal(
        api_key_id=row.id,
        name=row.name,
        scopes=read_scopes(row.scopes),
    )


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
    """
    from app.database import async_session_factory  # noqa: PLC0415

    try:
        async with async_session_factory() as session:
            await session.execute(
                update(ApiKey)
                .where(ApiKey.id == api_key_id)
                .values(last_used_at=now or datetime.now(timezone.utc))
            )
            await session.commit()
    except Exception:
        logger.warning("api_keys: could not bump last_used_at for %s", api_key_id, exc_info=True)


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
    await record_event(
        session,
        event_type=API_KEY_REVOKED,
        object_type="system",
        object_id=row.id,
        actor=actor,
        payload={"name": row.name},
    )
    return True

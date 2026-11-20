"""The backup destinations config row (spec section 9.3, amended).

One ``config`` row, key ``backup_destinations``, holding the full destination
list -- the LLM-provider shape, and the same credential posture as per-repo
git tokens (``repo_manager.py``, ``git_token_<repo_id>``): secrets live in the
row, are masked on every read that leaves the process, and never appear in a
job ``config_schema`` (``FieldDescriptor.default`` is typed ``int``, so a URL,
a bucket or a key cannot be smuggled in there even by accident).

The age *recipient* (public key) is stored here and encrypts; the identity
(private key) must never be stored in this database -- a snapshot carrying its
own decryption key is not encrypted at rest, because every dump would include
the key that opens it. Section 9.4 rule 1 is enforced at save: every non-local
destination must carry a recipient, so no later code path has to remember to
check before bytes leave the host.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config

BACKUP_DESTINATIONS_KEY = "backup_destinations"
MASKED = "***"
#: Per settings group, the fields that never leave the process in the clear.
SECRET_FIELDS: dict[str, tuple[str, ...]] = {
    "ssh": ("private_key",),
    "s3": ("secret_access_key",),
    "worker": ("token",),
}

KINDS = ("local", "ssh", "s3", "worker")


class DestinationInvalid(ValueError):
    """A destination list the door must refuse, with a message for the operator."""


class SshSettings(BaseModel):
    host: str
    port: int = 22
    user: str
    remote_dir: str
    #: A known_hosts line, pinned. Never trust-on-first-use: the first
    #: connection is exactly the one an attacker would want to intercept.
    host_key: str
    private_key: str


class S3Settings(BaseModel):
    endpoint_url: str
    bucket: str
    prefix: str = ""
    region: str = "auto"
    access_key_id: str
    secret_access_key: str


class WorkerSettings(BaseModel):
    """A darkmem backup worker's snapshot receiver (increment 7).

    The token is authorisation, not confidentiality: content arrives
    age-encrypted, so `age_recipient` is what protects the bytes and rule 1
    reaches this kind for that reason rather than by category.
    """

    url: str
    token: str


class DestinationConfig(BaseModel):
    name: str
    kind: str
    enabled: bool = True
    retention_keep: int = 14
    #: The attachment tarball family's own retention. Separate from
    #: `retention_keep` because the artefacts are orders of magnitude apart:
    #: fourteen whole-volume tarballs is a different disk commitment from
    #: fourteen dumps.
    attachments_retention_keep: int = 3
    age_recipient: str | None = None
    ssh: SshSettings | None = None
    s3: S3Settings | None = None
    worker: WorkerSettings | None = None


# ssh/scp take `user@host` ahead of `--`, so an option-shaped value there is
# an option, not an address (`-oProxyCommand=` runs a command).
_SSH_USER = re.compile(r"[A-Za-z0-9._][A-Za-z0-9._-]*")
_SSH_HOST = re.compile(r"[A-Za-z0-9_\[][A-Za-z0-9._:\[\]%-]*")

# The fields a stored secret is bound to: a masked secret is kept only while
# every one of them is unchanged, so a session cannot send a stored secret to a
# new endpoint without entering it again.
# The bucket and the access key id are bound too: a bucket elsewhere can grant
# the stored key write access. So is `age_recipient`, which decides who can
# read what the stored secret ships.
CONNECTION_FIELDS: dict[str, tuple[str, ...]] = {
    "ssh": ("host", "port", "user"),
    "s3": ("endpoint_url", "bucket", "access_key_id"),
    "worker": ("url",),
}


def _validate_ssh(name: str, ssh: SshSettings) -> None:
    if not _SSH_USER.fullmatch(ssh.user):
        raise DestinationInvalid(f"{name}: ssh user must be letters, digits, '.', '_' or '-', not starting with '-'")
    if not _SSH_HOST.fullmatch(ssh.host):
        raise DestinationInvalid(f"{name}: ssh host must be a hostname or IP address")
    if "\n" in ssh.remote_dir or "\r" in ssh.remote_dir:
        raise DestinationInvalid(f"{name}: ssh remote_dir must not contain a line break")


def _validate(items: list[DestinationConfig]) -> None:
    names = [d.name for d in items]
    if len(names) != len(set(names)):
        raise DestinationInvalid("destination names must be unique")
    for d in items:
        if not d.name.strip():
            raise DestinationInvalid("a destination needs a name")
        if d.kind not in KINDS:
            raise DestinationInvalid(f"unknown kind {d.kind!r}")
        if d.kind != "local" and not d.age_recipient:
            raise DestinationInvalid(
                f"{d.name}: encrypt before egress -- a non-local destination "
                f"requires an age recipient (spec section 9.4 rule 1)"
            )
        if d.kind == "ssh" and d.ssh is None:
            raise DestinationInvalid(f"{d.name}: ssh settings required")
        if d.ssh is not None:
            _validate_ssh(d.name, d.ssh)
        if d.kind == "s3" and d.s3 is None:
            raise DestinationInvalid(f"{d.name}: s3 settings required")
        if d.kind == "worker" and d.worker is None:
            raise DestinationInvalid(f"{d.name}: worker settings required")
        if d.retention_keep < 1 or d.retention_keep > 3650:
            raise DestinationInvalid(f"{d.name}: retention_keep out of range")
        if d.attachments_retention_keep < 1 or d.attachments_retention_keep > 3650:
            raise DestinationInvalid(
                f"{d.name}: attachments_retention_keep out of range"
            )


async def _load_row(session: AsyncSession) -> Config | None:
    return (
        await session.execute(
            select(Config).where(Config.key == BACKUP_DESTINATIONS_KEY)
        )
    ).scalar_one_or_none()


def mask_destination(d: DestinationConfig) -> DestinationConfig:
    out = d.model_copy(deep=True)
    for group, fields in SECRET_FIELDS.items():
        sub = getattr(out, group, None)
        if sub is None:
            continue
        for f in fields:
            if getattr(sub, f, None):
                setattr(sub, f, MASKED)
    return out


async def load_destinations(
    session: AsyncSession, *, masked: bool = True
) -> list[DestinationConfig]:
    row = await _load_row(session)
    raw = (row.value or {}).get("destinations", []) if row else []
    items = [DestinationConfig.model_validate(v) for v in raw]
    return [mask_destination(d) for d in items] if masked else items


async def save_destinations(
    session: AsyncSession, body: dict
) -> list[DestinationConfig]:
    try:
        items = [
            DestinationConfig.model_validate(v) for v in body.get("destinations", [])
        ]
    except ValidationError as exc:
        raise DestinationInvalid(str(exc)) from exc

    # A masked secret on PUT means "unchanged": resolve it against the stored
    # row before validating, the llm_providers MASKED_KEY contract. Resolving
    # after validation would let a mask satisfy a required-field check and then
    # be stored literally.
    stored = {d.name: d for d in await load_destinations(session, masked=False)}
    for d in items:
        prev = stored.get(d.name)
        for group, fields in SECRET_FIELDS.items():
            sub = getattr(d, group, None)
            if sub is None:
                continue
            prev_sub = getattr(prev, group, None) if prev else None
            for f in fields:
                if getattr(sub, f, None) != MASKED:
                    continue
                if prev_sub is None or not getattr(prev_sub, f, None):
                    raise DestinationInvalid(
                        f"{d.name}: masked {f} with no stored value"
                    )
                moved = [
                    c for c in CONNECTION_FIELDS.get(group, ())
                    if getattr(sub, c, None) != getattr(prev_sub, c, None)
                ]
                if d.age_recipient != prev.age_recipient:
                    moved.append("age_recipient")
                if moved:
                    raise DestinationInvalid(
                        f"{d.name}: {', '.join(moved)} changed, so enter {f} again"
                    )
                setattr(sub, f, getattr(prev_sub, f))

    _validate(items)
    payload = {"destinations": [d.model_dump() for d in items]}
    row = await _load_row(session)
    if row:
        row.value = payload
    else:
        session.add(Config(key=BACKUP_DESTINATIONS_KEY, value=payload))
    await session.commit()
    return items

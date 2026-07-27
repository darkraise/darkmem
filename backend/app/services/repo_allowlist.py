"""The auto-provision SSRF allowlist gate (doc 18 §6).

This module is the single enforcement point doc 18 *designs*; doc 05's
capture hook calls it and doc 10's Tier-C execution runs only past it.
Neither may re-implement or relax what is decided here.

**Allowlist, never blocklist.** A repository hint is caller-supplied text
that arrives over the unauthenticated MCP door, and `git clone` of an
arbitrary remote makes this box issue requests wherever the caller points
it. The rejected alternative — default-open with a blocklist of private
address ranges — loses to decimal-encoded addresses, IPv6-mapped IPv4,
link-local metadata endpoints, and (fatally) to DNS rebinding: validating
`evil.example` while it resolves publicly says nothing about where it
resolves at clone time. Naming the trusted hosts sidesteps the resolution
game entirely, which is why this gate performs **no DNS lookup, no HTTP
request, and no redirect following of any kind** — a hint is never
dereferenced, only parsed and compared. A redirect chain therefore cannot
matter: nothing here follows one.

The shipped default is an absent `repo_allowlist` config row, i.e. no
patterns, i.e. every hint refused — auto-provision is inert until the
operator opts in. Every rejection returns a reason from `REJECTION_REASONS`
so the journaled `repo_hint_rejected` event says *why*, and every rejection
is visible rather than fatal: the caller's memory ingests regardless.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config

logger = logging.getLogger(__name__)

REPO_ALLOWLIST_KEY = "repo_allowlist"

# `http` and `git://` are cleartext, `file://` is a local-file read, and git's
# `ext::` transport helper is arbitrary command execution. None has a
# legitimate auto-provision use, so the accepted set is closed at two.
ALLOWED_SCHEMES = frozenset({"https", "ssh"})

# The only userinfo an ssh remote may carry. A username is not a credential,
# but any other value is either meaningless or an attempt to make the host
# look like something it is not (`https://github.com@169.254.169.254/x`).
SSH_USER = "git"

MAX_HINT_CHARS = 512

REJECTION_REASONS: tuple[str, ...] = (
    "unparsable",
    "scheme_not_allowed",
    "credentials_in_url",
    "userinfo_not_allowed",
    "missing_host",
    "illegal_host",
    "explicit_port",
    "illegal_path",
    "path_traversal",
    "missing_repo_path",
    "not_allowlisted",
)

_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9\-._]*[a-z0-9])?$")
_PATH_RE = re.compile(r"^[A-Za-z0-9._\-/+]+$")
_SCP_RE = re.compile(r"^(?P<user>[A-Za-z0-9._\-]+)@(?P<host>[^/:@]+):(?P<path>[^/].*)$")


@dataclass(frozen=True)
class HintVerdict:
    """One hint's outcome. `reason` is empty exactly when `allowed`."""

    allowed: bool
    reason: str = ""
    remote: str = ""
    host: str = ""
    path: str = ""


@dataclass(frozen=True)
class _Normalized:
    scheme: str
    host: str
    path: str
    remote: str


def _normalize(raw: object) -> tuple[_Normalized | None, str]:
    if not isinstance(raw, str):
        return None, "unparsable"
    candidate = raw.strip()
    if not candidate or len(candidate) > MAX_HINT_CHARS:
        return None, "unparsable"
    if any(c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F for c in candidate):
        return None, "unparsable"

    if "://" not in candidate:
        scp = _SCP_RE.match(candidate)
        if not scp:
            # A bare `github.com/org/repo` is ambiguous about its transport,
            # and guessing one for attacker-supplied text is the wrong
            # direction to guess in.
            return None, "scheme_not_allowed"
        candidate = f"ssh://{scp['user']}@{scp['host']}/{scp['path']}"

    try:
        split = urlsplit(candidate)
    except ValueError:
        return None, "unparsable"

    scheme = split.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        return None, "scheme_not_allowed"

    try:
        username, password, hostname, port = (
            split.username, split.password, split.hostname, split.port,
        )
    except ValueError:
        return None, "unparsable"

    if password:
        return None, "credentials_in_url"
    if username and not (scheme == "ssh" and username == SSH_USER):
        return None, "userinfo_not_allowed"
    if not hostname:
        return None, "missing_host"

    host = hostname.lower().rstrip(".")
    if not _HOST_RE.match(host) or ".." in host:
        return None, "illegal_host"
    if port is not None:
        # The pattern language is host / *.host / optional path prefix and
        # cannot name a port, so a port cannot be allowlisted — and a port
        # swap on an allowlisted host reaches a service the operator never
        # named. Refusing is the fail-closed reading.
        return None, "explicit_port"

    path = split.path
    if not path or path == "/":
        return None, "missing_repo_path"
    if split.query or split.fragment or not _PATH_RE.match(path):
        return None, "illegal_path"
    segments = [s for s in path.split("/") if s]
    if any(s in (".", "..") for s in segments):
        return None, "path_traversal"
    if not segments:
        return None, "missing_repo_path"
    path = "/" + "/".join(segments)

    remote = (
        f"https://{host}{path}" if scheme == "https" else f"ssh://{SSH_USER}@{host}{path}"
    )
    return _Normalized(scheme=scheme, host=host, path=path, remote=remote), ""


def _host_matches(host: str, host_pattern: str) -> bool:
    if host_pattern.startswith("*."):
        suffix = host_pattern[1:]
        return host.endswith(suffix) and len(host) > len(suffix)
    return host == host_pattern


def _path_matches(path: str, path_pattern: str) -> bool:
    if not path_pattern:
        return True
    prefix = "/" + path_pattern.strip("/")
    if path_pattern.endswith("/*"):
        return path.startswith(prefix[: -len("/*")] + "/")
    return path == prefix


def _split_pattern(pattern: object) -> tuple[str, str] | None:
    if not isinstance(pattern, str):
        return None
    cleaned = pattern.strip().lower()
    if not cleaned or "://" in cleaned or "@" in cleaned or any(c.isspace() for c in cleaned):
        return None
    host_part, _, path_part = cleaned.partition("/")
    if not host_part:
        return None
    bare = host_part[2:] if host_part.startswith("*.") else host_part
    if not _HOST_RE.match(bare):
        return None
    return host_part, path_part


def evaluate_hint(raw: object, patterns: object) -> HintVerdict:
    """Decide one hint against one allowlist. Pure: no DNS, no I/O, no clone.

    An empty, absent or unusable pattern list refuses everything — the gate
    fails closed, so a misconfigured allowlist is inert rather than open.
    """
    normalized, reason = _normalize(raw)
    if normalized is None:
        return HintVerdict(allowed=False, reason=reason)

    parsed_patterns = []
    for pattern in patterns if isinstance(patterns, (list, tuple)) else ():
        split = _split_pattern(pattern)
        if split is None:
            logger.warning("repo_allowlist: ignoring unusable pattern %r", pattern)
            continue
        parsed_patterns.append(split)

    for host_pattern, path_pattern in parsed_patterns:
        if _host_matches(normalized.host, host_pattern) and _path_matches(
            normalized.path, path_pattern
        ):
            return HintVerdict(
                allowed=True,
                remote=normalized.remote,
                host=normalized.host,
                path=normalized.path,
            )

    return HintVerdict(
        allowed=False,
        reason="not_allowlisted",
        remote=normalized.remote,
        host=normalized.host,
        path=normalized.path,
    )


def validate_pattern(pattern: object) -> str | None:
    """Canonical form of one allowlist pattern, or ``None`` if invalid.

    Wraps ``_split_pattern`` — the exact parse `evaluate_hint` runs a stored
    pattern through at clone time — so the settings editor and the SSRF gate
    can never define "valid pattern" differently. Do not re-validate a
    pattern any other way; call this.
    """
    split = _split_pattern(pattern)
    if split is None:
        return None
    host_part, path_part = split
    return f"{host_part}/{path_part}" if path_part else host_part


async def load_allowlist(session: AsyncSession) -> list:
    """Read the `repo_allowlist` config row. Absent row means no patterns."""
    row = (
        await session.execute(select(Config).where(Config.key == REPO_ALLOWLIST_KEY))
    ).scalar_one_or_none()
    if row is None:
        return []
    value = row.value
    if isinstance(value, dict):
        value = value.get("patterns", [])
    if not isinstance(value, list):
        logger.warning(
            "repo_allowlist: config row is %s, not a list — refusing every hint",
            type(value).__name__,
        )
        return []
    return value

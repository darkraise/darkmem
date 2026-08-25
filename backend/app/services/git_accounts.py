"""Git forge accounts — CRUD plus the token verification that mints one.

An account is created only from a token the forge itself accepted: the username
is what the forge reported for that token, never what the operator typed. The
cost is that a host with no outbound network cannot add an account at all.

**On SSRF.** Verification fetches an operator-named host, and there is
deliberately no private-address blocklist: `host` exists so a self-hosted Gitea
or GitLab on the LAN can be named, so refusing RFC1918 and loopback would refuse
the feature's main use rather than an attack. The boundary is that both callers
require an authenticated operator, who can already point `repos.url` and an
`llm_providers.base_url` at any host and have the server connect. What IS closed
is everything that makes this more than that operator's own outbound request:
the scheme is fixed https by the forge template, `_validate_host` refuses any
character that could steer the request off the named authority, redirects are
not followed so the token cannot be re-sent to a host the target chose, and no
upstream status or transport error reaches the response — those go to the log,
because the difference between "refused" and "timed out" is a port-scan oracle.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import Repository
from app.models.git_account import GitAccount
from app.schemas.git_account import (
    GitAccountCreate,
    GitAccountOut,
    GitAccountUpdate,
)
from app.services.git_forges import api_base, get_forge

logger = logging.getLogger(__name__)

VERIFY_TIMEOUT_SECONDS = 15.0


class GitAccountError(Exception):
    """A caller-visible failure; the route maps it to a status code."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GitAccountInUse(GitAccountError):
    def __init__(self, message: str, repos: list[dict[str, str]]) -> None:
        super().__init__(message, status_code=409)
        self.repos = repos


def token_hint(token: str) -> str:
    """Last four characters, the only part of a token that may leave the process."""
    return token[-4:] if len(token) >= 4 else "*" * len(token)


async def verify_token(
    token: str, provider: str, host: str | None = None,
) -> tuple[str, str, str | None]:
    """Resolve a token's own identity at the forge.

    Returns ``(host, username, scopes)``. Raises :class:`GitAccountError` when
    the forge rejects the token or cannot be reached — a token that cannot be
    verified is never stored.
    """
    forge = get_forge(provider)
    resolved_host = host or forge.default_host
    url = api_base(provider, resolved_host) + forge.identity_path
    headers = {
        forge.auth_header: forge.auth_value_template.format(token=token),
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(
            timeout=VERIFY_TIMEOUT_SECONDS,
            # Pinned rather than left to httpx's default: a 3xx to another host
            # would re-send the Authorization header there, handing the
            # operator's token to whatever the named host chose to point at.
            follow_redirects=False,
        ) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        # The exception text carries the resolved address and the transport
        # failure mode, which together answer "is there something listening on
        # that host and port" — a probe oracle for anyone who can reach this
        # endpoint. It goes to the log, where the operator can read it, and not
        # into the response.
        logger.warning("Verifying a %s token at %s failed: %s", forge.label, resolved_host, exc)
        raise GitAccountError(
            f"Could not reach {forge.label} at {resolved_host}.", status_code=502,
        ) from None

    if response.status_code in (401, 403):
        raise GitAccountError(
            f"{forge.label} rejected the token. "
            "Check that it is current and has repository read access.",
            status_code=422,
        )
    if response.status_code >= 400:
        logger.warning(
            "Verifying a %s token at %s returned %s",
            forge.label, resolved_host, response.status_code,
        )
        raise GitAccountError(
            f"{resolved_host} did not answer as a {forge.label} API.", status_code=502,
        )

    try:
        payload = response.json()
    except ValueError:
        raise GitAccountError(
            f"{resolved_host} did not answer as a {forge.label} API.", status_code=502,
        ) from None

    username = payload.get(forge.identity_field) if isinstance(payload, dict) else None
    if not username:
        raise GitAccountError(
            f"{forge.label} did not report an account name for this token.",
            status_code=502,
        )

    scopes = None
    if forge.scope_header:
        # Absent for GitHub fine-grained PATs, which is the token type GitHub
        # now recommends. Nothing may gate on this being populated.
        raw = response.headers.get(forge.scope_header)
        scopes = raw.strip() or None if raw else None

    return resolved_host, str(username), scopes


class GitAccountService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _repo_counts(self) -> dict[uuid.UUID, int]:
        rows = (
            await self.session.execute(
                select(Repository.git_account_id, func.count())
                .where(Repository.git_account_id.is_not(None))
                .group_by(Repository.git_account_id)
            )
        ).all()
        return {row[0]: row[1] for row in rows}

    @staticmethod
    def to_out(account: GitAccount, repo_count: int = 0) -> GitAccountOut:
        return GitAccountOut(
            id=account.id,
            label=account.label,
            provider=account.provider,
            host=account.host,
            username=account.username,
            token_hint=token_hint(account.token),
            scopes=account.scopes,
            is_default=account.is_default,
            last_verified_at=account.last_verified_at,
            repo_count=repo_count,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    async def list(self) -> list[GitAccountOut]:
        accounts = (
            await self.session.execute(
                select(GitAccount).order_by(
                    GitAccount.provider, GitAccount.host, GitAccount.label,
                )
            )
        ).scalars().all()
        counts = await self._repo_counts()
        return [self.to_out(a, counts.get(a.id, 0)) for a in accounts]

    async def get(self, account_id: uuid.UUID) -> GitAccount | None:
        return await self.session.get(GitAccount, account_id)

    async def get_default(self, provider: str, host: str | None = None) -> GitAccount | None:
        """The default account for a forge, or None.

        ``host`` narrows to one install; omitted, it prefers the vendor's own
        host so a repo URL that named no host does not land on an Enterprise
        credential.
        """
        try:
            forge = get_forge(provider)
        except ValueError:
            return None
        stmt = select(GitAccount).where(
            GitAccount.provider == provider, GitAccount.is_default.is_(True),
        )
        if host:
            stmt = stmt.where(GitAccount.host == host)
        accounts = (await self.session.execute(stmt)).scalars().all()
        if not accounts:
            return None
        for account in accounts:
            if account.host == forge.default_host:
                return account
        return accounts[0]

    async def _clear_other_defaults(
        self, provider: str, host: str, keep: uuid.UUID | None,
    ) -> None:
        """Demote the incumbent default before promoting a new one.

        The partial unique index would otherwise reject the promotion, and
        "there can be only one" is the behaviour an operator expects from a
        radio button, not an error.
        """
        stmt = (
            update(GitAccount)
            .where(
                GitAccount.provider == provider,
                GitAccount.host == host,
                GitAccount.is_default.is_(True),
            )
            .values(is_default=False)
        )
        if keep is not None:
            stmt = stmt.where(GitAccount.id != keep)
        await self.session.execute(stmt)

    async def _assert_label_free(
        self, provider: str, host: str, label: str, exclude: uuid.UUID | None = None,
    ) -> None:
        stmt = select(GitAccount.id).where(
            GitAccount.provider == provider,
            GitAccount.host == host,
            GitAccount.label == label,
        )
        if exclude is not None:
            stmt = stmt.where(GitAccount.id != exclude)
        if (await self.session.execute(stmt)).first() is not None:
            raise GitAccountError(
                f"An account named {label!r} already exists for {host}.",
                status_code=409,
            )

    async def create(self, data: GitAccountCreate) -> GitAccount:
        host, username, scopes = await verify_token(data.token, data.provider, data.host)
        await self._assert_label_free(data.provider, host, data.label)

        # Demote the incumbent BEFORE the insert: the partial unique index is
        # checked per statement, so promoting first and demoting after fails on
        # the INSERT itself rather than resolving.
        is_default = data.is_default
        if is_default:
            await self._clear_other_defaults(data.provider, host, keep=None)
        else:
            # The first account for a forge becomes its default: an operator
            # who adds exactly one has plainly chosen it.
            is_default = await self.get_default(data.provider, host) is None

        account = GitAccount(
            label=data.label,
            provider=data.provider,
            host=host,
            username=username,
            token=data.token,
            scopes=scopes,
            is_default=is_default,
            last_verified_at=datetime.now(timezone.utc),
        )
        self.session.add(account)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def update(self, account_id: uuid.UUID, data: GitAccountUpdate) -> GitAccount | None:
        account = await self.session.get(GitAccount, account_id)
        if not account:
            return None

        if data.label is not None and data.label.strip() != account.label:
            label = data.label.strip()
            if not label:
                raise GitAccountError("label must not be blank", status_code=422)
            await self._assert_label_free(
                account.provider, account.host, label, exclude=account.id,
            )
            account.label = label

        # Re-verify only when the token itself changes, so relabelling and
        # promoting a default keep working on a host with no outbound network.
        if data.token is not None and data.token != account.token:
            _, username, scopes = await verify_token(
                data.token, account.provider, account.host,
            )
            account.token = data.token
            account.username = username
            account.scopes = scopes
            account.last_verified_at = datetime.now(timezone.utc)

        if data.is_default is not None:
            if data.is_default:
                await self._clear_other_defaults(
                    account.provider, account.host, account.id,
                )
                account.is_default = True
            else:
                account.is_default = False

        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def repos_using(self, account_id: uuid.UUID) -> list[Repository]:
        return list(
            (
                await self.session.execute(
                    select(Repository)
                    .where(Repository.git_account_id == account_id)
                    .order_by(Repository.name)
                )
            ).scalars().all()
        )

    async def delete(
        self, account_id: uuid.UUID, reassign_to: uuid.UUID | None = None,
    ) -> bool:
        account = await self.session.get(GitAccount, account_id)
        if not account:
            return False

        repos = await self.repos_using(account_id)
        if repos:
            if reassign_to is None:
                raise GitAccountInUse(
                    f"{len(repos)} repositor{'y' if len(repos) == 1 else 'ies'} "
                    f"still use {account.label!r}. Reassign them first.",
                    [{"id": str(r.id), "name": r.name} for r in repos],
                )
            target = await self.session.get(GitAccount, reassign_to)
            if target is None or target.id == account_id:
                raise GitAccountError(
                    "reassign_to must name a different, existing account.",
                    status_code=422,
                )
            # Already-cloned repos are not re-cloned; the next fetch simply
            # authenticates with the new token.
            await self.session.execute(
                update(Repository)
                .where(Repository.git_account_id == account_id)
                .values(git_account_id=target.id)
            )

        was_default = account.is_default
        await self.session.delete(account)
        await self.session.flush()

        if was_default:
            # Leave the forge with a default rather than silently none, so a
            # later repo add still preselects something.
            successor = (
                await self.session.execute(
                    select(GitAccount)
                    .where(
                        GitAccount.provider == account.provider,
                        GitAccount.host == account.host,
                    )
                    .order_by(GitAccount.created_at, GitAccount.id)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if successor is not None:
                successor.is_default = True

        await self.session.commit()
        return True

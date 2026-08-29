import asyncio
import logging
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeFile, CodeSymbol, Repository
from app.models.config import Config
from app.schemas.code import RepoCreate, RepoUpdate

logger = logging.getLogger(__name__)

REPOS_BASE_DIR = Path(os.environ.get("DARKMEM_REPOS_DIR", "./data/repositories"))


def _sanitize_url(text: str) -> str:
    return re.sub(r'x-access-token:[^@]+@', 'x-access-token:***@', text)


# Common system / credential trees we never want the indexer to walk into,
# even on a personal-use deployment. Not exhaustive — defence against the
# typo class of foot-gun, not the malicious-admin class.
_LOCAL_PATH_BLOCKLIST: tuple[str, ...] = (
    "/etc", "/root", "/var", "/sys", "/proc", "/boot", "/dev",
    "/private/etc", "/private/var",  # macOS
)
_HOME_SUBPATH_BLOCKLIST: tuple[str, ...] = (
    ".ssh", ".aws", ".gnupg", ".config", ".kube", ".docker", ".npm", ".cache",
)


def validate_local_path(raw: str, *, must_not_be_repo: bool = False) -> Path:
    """Resolve ``raw`` and reject it if the indexer shouldn't read from there.

    Raises ``ValueError`` with a single sentence explaining the reason.
    Returns the resolved ``Path`` so callers can use it directly.

    When ``must_not_be_repo=True``, also rejects paths whose immediate
    contents include a ``.git`` directory — used by the setup wizard's
    "Use this folder" guard so the chosen base path is never itself a
    repository (which would clash with detect-children-as-repos logic).
    """
    if not raw or not raw.strip():
        raise ValueError("local_path must not be empty")
    resolved = Path(raw).expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"local_path does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"local_path is not a directory: {resolved}")
    posix = resolved.as_posix()
    for blocked in _LOCAL_PATH_BLOCKLIST:
        if posix == blocked or posix.startswith(blocked + "/"):
            raise ValueError(f"local_path is inside a blocked system tree: {blocked}")
    home = Path.home().resolve().as_posix()
    if posix.startswith(home + "/"):
        rest = posix[len(home) + 1:]
        first = rest.split("/", 1)[0]
        if first in _HOME_SUBPATH_BLOCKLIST:
            raise ValueError(
                f"local_path is inside a blocked credential tree: ~/{first}"
            )
    if must_not_be_repo and (resolved / ".git").is_dir():
        raise ValueError(f"local_path is itself a git repository: {resolved}")
    return resolved


def _force_remove(func, path, exc_info):
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)


async def add_git_safe_directory(path: Path) -> bool:
    """Whitelist ``path`` in the backend user's git ``safe.directory`` list.

    git refuses to fetch / pull / reset against a working tree whose
    owner uid differs from the process uid (the "fatal: detected
    dubious ownership in repository at '<path>'" error). This shows
    up most often when:

    - The setup wizard registers a folder that the operator cloned
      while running as a different user (root vs their own account).
    - The backend runs in Docker as uid 1000 but the bind-mounted
      host folder is owned by some other uid.
    - On Windows, the working tree was cloned by a different account
      than the one running the dev server.

    Running ``git config --global --add safe.directory <path>`` once
    per registered repo records the trust in the running user's
    ``~/.gitconfig``. The directive is exact-path, so adding a parent
    folder does NOT whitelist its children — each detected repo must
    be added on its own. The ``--add`` form is idempotent at the user
    level (duplicate entries are accepted and harmless), so retrying
    a creation that previously succeeded does not error.

    Best-effort: if git isn't installed, ``HOME`` is not writable, or
    the subprocess otherwise fails, we log and return ``False``. The
    caller continues with the repo creation regardless — the worst
    case is the same dubious-ownership error the operator would have
    hit before this helper existed.
    """
    import subprocess
    cmd = ["git", "config", "--global", "--add", "safe.directory", str(path)]
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, timeout=10),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("git safe.directory add failed for %s: %s", path, exc)
        return False
    if result.returncode != 0:
        logger.warning(
            "git safe.directory add failed for %s: rc=%d stderr=%s",
            path, result.returncode, result.stderr.decode(errors="replace").strip(),
        )
        return False
    logger.info("Added %s to git safe.directory", path)
    return True


class RepoManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _resolve_create_account(self, data: RepoCreate) -> UUID | None:
        """Which account a new repo authenticates with.

        An explicit ``auth_token`` keeps the per-repo custom-token path. An
        explicitly sent ``git_account_id`` — including ``null`` — is honoured as
        the caller's decision. Only an omitted field falls back to the forge's
        default, so what a repo authenticates with is always a stored value and
        never resolved afresh at fetch time.
        """
        if data.auth_token:
            return None
        if "git_account_id" in data.model_fields_set:
            return data.git_account_id
        from app.services.git_accounts import GitAccountService
        host = urlparse(data.url).hostname if data.url else None
        account = await GitAccountService(self.session).get_default(
            data.provider, host,
        )
        return account.id if account else None

    async def create(self, data: RepoCreate) -> Repository:
        # Validate local_path early so a typo can't end up writing a row
        # whose indexer will walk into /etc or ~/.ssh on the next sync.
        validated_local_path: str | None = None
        if data.local_path:
            try:
                validated_local_path = str(validate_local_path(data.local_path))
            except ValueError as e:
                raise ValueError(str(e)) from None
            # Pre-emptively whitelist the path in the backend user's git
            # safe.directory so the first fetch / pull doesn't trip the
            # "dubious ownership" guard. Best-effort — see helper docstring.
            await add_git_safe_directory(Path(validated_local_path))
        repo = Repository(
            name=data.name,
            url=data.url,
            local_path=validated_local_path,
            provider=data.provider,
            default_branch=data.default_branch,
            auto_sync=data.auto_sync,
            status="cloning" if data.url else "ready",
            status_message="Cloning repository..." if data.url else None,
            git_account_id=await self._resolve_create_account(data),
        )
        self.session.add(repo)
        await self.session.flush()

        if data.auth_token:
            repo.auth_token_ref = f"git_token_{repo.id}"
            config = Config(key=repo.auth_token_ref, value={"token": data.auth_token})
            self.session.add(config)

        await self.session.commit()
        await self.session.refresh(repo)

        if data.url:
            from app.services.task_registry import TaskRegistry
            task = asyncio.create_task(self._clone_in_background(repo.id, data))
            TaskRegistry.register(repo.id, "clone", task, "Cloning repository...")

        return repo

    async def _clone_in_background(self, repo_id: UUID, data: RepoCreate) -> None:
        from app.api.websocket import event_manager
        from app.database import async_session_factory
        try:
            async with async_session_factory() as session:
                repo = (await session.execute(
                    select(Repository).where(Repository.id == repo_id)
                )).scalar_one_or_none()
                if not repo:
                    return

                await event_manager.broadcast("repo.clone_started", {"repo_id": str(repo_id), "name": repo.name})
                manager = RepoManager(session)
                await manager._clone_repo(repo)
                repo.status = "ready"
                repo.status_message = None
                logger.info(f"Background clone completed for {repo.name}")
                await session.commit()
                await event_manager.broadcast("repo.clone_completed", {"repo_id": str(repo_id), "name": repo.name})
        except Exception as e:
            logger.error(f"Background clone failed for repo {repo_id}: {e}")
            await event_manager.broadcast("repo.clone_failed", {"repo_id": str(repo_id), "error": _sanitize_url(str(e))[:200]})
            try:
                async with async_session_factory() as session:
                    repo = (await session.execute(
                        select(Repository).where(Repository.id == repo_id)
                    )).scalar_one_or_none()
                    if repo:
                        repo.status = "error"
                        repo.status_message = _sanitize_url(str(e))[:500]
                        await session.commit()
            except Exception as inner_e:
                logger.error("Failed to set error status for repo %s: %s", repo_id, inner_e)

    async def get(self, repo_id: UUID) -> Repository | None:
        return await self.session.get(Repository, repo_id)

    # The statuses that mean "a run already owns this repo". Named once: the
    # webhook route, the reindex route and the polling job all have to agree,
    # and they used to agree by three copies of the same tuple.
    BUSY_STATUSES = ("indexing", "cloning")

    async def claim_for_indexing(self, repo_id: UUID, *, message: str) -> bool:
        """Atomically take the indexing claim. False means someone else holds it.

        Read-then-write is not enough and that is the whole point of this method
        (T4.16). The webhook route, the reindex route and `repo_sync` each used
        to check `repo.status` and then assign it, so two callers could both
        read `ready` and both proceed — `repo_sync` did not read the status at
        all, so a poll tick landing inside a webhook run indexed the same
        repository twice concurrently. The predicate lives in the UPDATE, so
        exactly one caller's statement can match.

        Commits, because the claim is only worth anything once it is visible to
        the other callers — a claim held in an uncommitted transaction is a
        claim nobody else can lose.
        """
        claimed = (await self.session.execute(
            update(Repository)
            .where(
                Repository.id == repo_id,
                Repository.status.notin_(self.BUSY_STATUSES),
            )
            .values(status="indexing", status_message=message)
            .returning(Repository.id)
        )).scalar_one_or_none()
        await self.session.commit()
        return claimed is not None

    async def list_all(self) -> list[dict]:
        repos = (await self.session.execute(select(Repository))).scalars().all()

        file_counts = dict(
            (await self.session.execute(
                select(CodeFile.repo_id, func.count(CodeFile.id)).group_by(CodeFile.repo_id)
            )).all()
        )

        symbol_counts_q = (
            select(CodeFile.repo_id, func.count(CodeSymbol.id))
            .join(CodeSymbol, CodeSymbol.file_id == CodeFile.id)
            .group_by(CodeFile.repo_id)
        )
        symbol_counts = dict((await self.session.execute(symbol_counts_q)).all())

        result = []
        for repo in repos:
            result.append({
                "repo": repo,
                "file_count": file_counts.get(repo.id, 0),
                "symbol_count": symbol_counts.get(repo.id, 0),
            })
        return result

    async def update(self, repo_id: UUID, data: RepoUpdate) -> Repository | None:
        repo = await self.session.get(Repository, repo_id)
        if not repo:
            return None

        update_fields = data.model_dump(exclude_unset=True, exclude={"auth_token"})
        for field, value in update_fields.items():
            setattr(repo, field, value)

        # Selecting an account retires the repo's own token: leaving the config
        # row behind would keep a credential on disk that nothing reads, and
        # resurrect it the moment the account is cleared again.
        if data.git_account_id is not None and data.auth_token is None:
            await self._drop_custom_token(repo)

        if data.auth_token is not None:
            token_key = f"git_token_{repo.id}"
            existing = await self.session.get(Config, token_key)
            if existing:
                existing.value = {"token": data.auth_token}
            else:
                self.session.add(Config(key=token_key, value={"token": data.auth_token}))
            repo.auth_token_ref = token_key
            repo.git_account_id = None

        await self.session.commit()
        await self.session.refresh(repo)
        return repo

    async def _drop_custom_token(self, repo: Repository) -> None:
        if not repo.auth_token_ref:
            return
        config = await self.session.get(Config, repo.auth_token_ref)
        if config:
            await self.session.delete(config)
        repo.auth_token_ref = None

    async def delete(self, repo_id: UUID) -> bool:
        from app.services.pipeline_failures import PipelineFailureService
        from app.api.websocket import event_manager
        failure_svc = PipelineFailureService(self.session, broadcast=event_manager.broadcast)
        await failure_svc.forget_all_for_repo(repo_id)

        repo = await self.session.get(Repository, repo_id)
        if not repo:
            return False

        # T2.96's withdrawal half: entities.repo_ids[] / entity_relations.repo_ids[]
        # carry no foreign key to `repositories`, so deleting the row below would
        # otherwise leave a dangling id in place (self-healed only the next time
        # something else strips that entity). Stripping here, before the row is
        # gone and in the same transaction as its removal, keeps the withdrawal
        # atomic with the deletion rather than deferred to a later sweep. Orphans
        # this leaves behind (no live memory, no live repo, no surviving relation)
        # are removed inline by strip_repo_assertions itself, the same self-healing
        # `delete_by_memory_id` does on the memory side — graph_orphan_cleanup is
        # not involved.
        from app.repositories.graph import PostgresGraphRepository
        await PostgresGraphRepository(self.session).strip_repo_assertions(repo_id)

        if repo.auth_token_ref:
            config = await self.session.get(Config, repo.auth_token_ref)
            if config:
                await self.session.delete(config)

        clone_dir = self._clone_path(repo)
        if clone_dir.exists():
            shutil.rmtree(clone_dir, onexc=_force_remove)

        await self.session.delete(repo)
        await self.session.commit()
        return True

    async def mark_periodic_sync_failure(
        self, repo_id: UUID, error: str | Exception,
    ) -> Repository | None:
        """Record a periodic-sync failure on the repo row and disable the
        indexing lane.

        The indexing loop in ``app.services.job_runners.make_repo_sync_runner``
        calls this when a repo's ``CodePipeline.run`` raises (typically a git
        fetch / pull error). Without this, the loop would re-attempt the same
        repo every tick — flooding logs and the upstream git server with
        the same failing request.

        The row is updated to ``status='error'`` with the sanitized error
        in ``status_message`` (truncated to 500 chars) and
        ``index_on_commit_enabled=False`` so subsequent ticks skip indexing
        it. ``fetch_enabled`` is left alone: a transient network failure must
        not silently turn off a setting the operator chose. The user can
        re-enable from the Edit Repo dialog after fixing the underlying
        issue (auth, network, branch rename, etc.).
        """
        repo = await self.session.get(Repository, repo_id)
        if not repo:
            return None
        message = _sanitize_url(str(error))[:500]
        # CodePipeline.run() already set and committed its own terminal status
        # for this failure, including "stale" when it kept the prior graph
        # rather than wiping it; don't overwrite that back to a bare "error".
        if repo.status != "stale":
            repo.status = "error"
            repo.status_message = message
        repo.index_on_commit_enabled = False
        await self.session.commit()
        await self.session.refresh(repo)
        logger.warning(
            "Disabled index-on-commit for repo %s (%s) after periodic-sync failure: %s",
            repo.name, repo_id, message[:200],
        )
        return repo

    async def account_labels(self) -> dict[UUID, str]:
        """Every account id to its label, for the denormalised response field.

        One query for the whole (tiny) table rather than one per repo row.
        """
        from app.models.git_account import GitAccount
        rows = (
            await self.session.execute(select(GitAccount.id, GitAccount.label))
        ).all()
        return {row[0]: row[1] for row in rows}

    async def get_auth_token(self, repo: Repository) -> str | None:
        credential = await self.get_credential(repo)
        return credential[0] if credential else None

    async def get_credential(self, repo: Repository) -> tuple[str, str] | None:
        """``(token, provider)`` for this repo, or None.

        The provider rides along because the git username in front of the token
        differs per forge; resolving the token without it is what silently
        breaks a non-GitHub clone.
        """
        if repo.git_account_id:
            from app.models.git_account import GitAccount
            account = await self.session.get(GitAccount, repo.git_account_id)
            if account:
                return account.token, account.provider
        if repo.auth_token_ref:
            config = await self.session.get(Config, repo.auth_token_ref)
            if config:
                token = config.value.get("token")
                if token:
                    return token, repo.provider
        return None

    async def pull_repo(self, repo: Repository) -> str | None:
        cwd = self.repo_working_dir(repo)
        # local_path repos point at the operator's OWN checkout; that working
        # tree must never be rmtree'd, re-cloned (the reclone fallback below)
        # or rewound (the fast-forward branch below).
        is_local = bool(repo.local_path)

        needs_clone = not cwd.exists() or not (cwd / ".git").exists()

        if not needs_clone:
            try:
                credential = await self.get_credential(repo)
                token = credential[0] if credential else None
                env: dict[str, str] = {}
                # Fetch from an explicit (optionally authed) URL rather than
                # persisting the token into .git/config via `remote set-url`;
                # reset to FETCH_HEAD since the remote-tracking ref isn't updated
                # when fetching from a bare URL.
                fetch_target = "origin"
                if token and repo.url:
                    fetch_target = self._auth_url(repo.url, token, credential[1])
                    # Fail fast instead of hanging on an interactive credential
                    # prompt if the embedded token is rejected.
                    env["GIT_TERMINAL_PROMPT"] = "0"

                await self._run_git(cwd, ["git", "fetch", fetch_target, repo.default_branch], env=env)
                if is_local:
                    # `reset --hard` moves the branch ref as well as the tree, so
                    # on the operator's own checkout it discards uncommitted edits
                    # and any commit they have not pushed. `--ff-only` advances or
                    # refuses; a refusal lands in the RuntimeError branch below,
                    # which leaves the tree alone and lets the caller read HEAD.
                    await self._run_git(cwd, ["git", "merge", "--ff-only", "FETCH_HEAD"], env=env)
                else:
                    await self._run_git(cwd, ["git", "reset", "--hard", "FETCH_HEAD"], env=env)

                result = await self._run_git(cwd, ["git", "rev-parse", "HEAD"], env=env)
                return result.strip() if result else None
            except RuntimeError as e:
                if is_local:
                    # Leave the operator's working tree intact; the caller reads
                    # HEAD from the existing checkout.
                    logger.warning("Pull failed for local repo %s (working tree left intact): %s", repo.name, e)
                    return None
                logger.warning("Pull failed for %s, will re-clone: %s", repo.name, e)
                needs_clone = True

        if needs_clone and repo.url and not is_local:
            if cwd.exists():
                shutil.rmtree(cwd, onexc=_force_remove)
            await self._clone_repo(repo)
            cwd = self._clone_path(repo)
            result = await self._run_git(cwd, ["git", "rev-parse", "HEAD"])
            return result.strip() if result else None

        return None

    def repo_working_dir(self, repo: Repository) -> Path:
        if repo.local_path:
            # Defence-in-depth: re-validate at every access so a row that
            # pre-dates the validator (or had its path mutated outside the
            # service) cannot drag the indexer into a blocked tree.
            return validate_local_path(repo.local_path)
        return self._clone_path(repo)

    async def _clone_repo(self, repo: Repository) -> None:
        if not repo.url:
            return

        # Defence-in-depth: rows can be created via paths other than RepoCreate,
        # so re-validate the URL and branch before they reach the git argv.
        from app.schemas.code import validate_git_ref, validate_repo_url
        validate_repo_url(repo.url)
        validate_git_ref(repo.default_branch)

        dest = self._clone_path(repo)
        if dest.exists():
            shutil.rmtree(dest, onexc=_force_remove)

        dest.parent.mkdir(parents=True, exist_ok=True)

        url = repo.url
        credential = await self.get_credential(repo)
        token = credential[0] if credential else None
        if token:
            url = self._auth_url(repo.url, token, credential[1])

        abs_dest = str(dest.resolve())
        cmd = ["git", "clone", "--branch", repo.default_branch, "--single-branch", url, abs_dest]
        await self._run_git(dest.parent, cmd)
        # git clone records the (token-bearing) URL in .git/config; reset the
        # remote to the bare URL so the credential isn't persisted on disk.
        if token:
            try:
                await self._run_git(dest, ["git", "remote", "set-url", "origin", repo.url])
            except RuntimeError:
                logger.warning("Failed to scrub auth token from %s remote URL", repo.name)

    @staticmethod
    def _auth_url(url: str, token: str, provider: str = "github") -> str:
        from app.services.git_forges import FORGES
        parsed = urlparse(url)
        # GitHub takes any username and reads the token as the password, but
        # GitLab accepts only `oauth2`, so this is not cosmetic. An unknown
        # provider keeps GitHub's spelling, which is the widest-accepted one.
        forge = FORGES.get(provider)
        git_username = forge.git_username if forge else "x-access-token"
        netloc = f"{git_username}:{token}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        authed = parsed._replace(netloc=netloc)
        return urlunparse(authed)

    @staticmethod
    async def _run_git(cwd: Path, cmd: list[str], env: dict[str, str] | None = None) -> str:
        import subprocess
        full_env = {**os.environ, **(env or {})}
        try:
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd, cwd=str(cwd), capture_output=True, env=full_env,
                    timeout=300,
                ),
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"git command timed out after 300s: {_sanitize_url(' '.join(cmd))}")
        stderr_text = result.stderr.decode()
        if result.returncode != 0:
            if "Clone succeeded, but checkout failed" in stderr_text:
                logger.warning("git clone succeeded with checkout warning: %s", stderr_text.strip())
            else:
                logger.error("git command failed: %s\nstderr: %s", _sanitize_url(" ".join(cmd)), _sanitize_url(stderr_text))
                raise RuntimeError(f"git command failed: {_sanitize_url(stderr_text)}")
        return result.stdout.decode()

    @staticmethod
    def _clone_path(repo: Repository) -> Path:
        return REPOS_BASE_DIR / str(repo.id)

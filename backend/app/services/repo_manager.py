import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeFile, CodeSymbol, Repository
from app.models.config import Config
from app.schemas.code import RepoCreate, RepoUpdate

logger = logging.getLogger(__name__)

REPOS_BASE_DIR = Path(os.environ.get("DARKMEM_REPOS_DIR", "./data/repositories"))


class RepoManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: RepoCreate) -> Repository:
        repo = Repository(
            name=data.name,
            url=data.url,
            local_path=data.local_path,
            provider=data.provider,
            default_branch=data.default_branch,
            sync_interval_minutes=data.sync_interval_minutes,
            status="cloning" if data.url else "ready",
            status_message="Cloning repository..." if data.url else None,
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
        from app.database import async_session_factory
        try:
            async with async_session_factory() as session:
                repo = (await session.execute(
                    select(Repository).where(Repository.id == repo_id)
                )).scalar_one_or_none()
                if not repo:
                    return

                manager = RepoManager(session)
                await manager._clone_repo(repo)
                repo.status = "ready"
                repo.status_message = None
                logger.info(f"Background clone completed for {repo.name}")
                await session.commit()
        except Exception as e:
            logger.error(f"Background clone failed for repo {repo_id}: {e}")
            try:
                async with async_session_factory() as session:
                    repo = (await session.execute(
                        select(Repository).where(Repository.id == repo_id)
                    )).scalar_one_or_none()
                    if repo:
                        repo.status = "error"
                        repo.status_message = str(e)[:500]
                        await session.commit()
            except Exception as inner_e:
                logger.error("Failed to set error status for repo %s: %s", repo_id, inner_e)

    async def get(self, repo_id: UUID) -> Repository | None:
        return await self.session.get(Repository, repo_id)

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

        if data.auth_token is not None:
            token_key = f"git_token_{repo.id}"
            existing = await self.session.get(Config, token_key)
            if existing:
                existing.value = {"token": data.auth_token}
            else:
                self.session.add(Config(key=token_key, value={"token": data.auth_token}))
            repo.auth_token_ref = token_key

        await self.session.commit()
        await self.session.refresh(repo)
        return repo

    async def delete(self, repo_id: UUID) -> bool:
        repo = await self.session.get(Repository, repo_id)
        if not repo:
            return False

        if repo.auth_token_ref:
            config = await self.session.get(Config, repo.auth_token_ref)
            if config:
                await self.session.delete(config)

        clone_dir = self._clone_path(repo)
        if clone_dir.exists():
            shutil.rmtree(clone_dir)

        await self.session.delete(repo)
        await self.session.commit()
        return True

    async def get_auth_token(self, repo: Repository) -> str | None:
        if not repo.auth_token_ref:
            return None
        config = await self.session.get(Config, repo.auth_token_ref)
        if not config:
            return None
        return config.value.get("token")

    async def pull_repo(self, repo: Repository) -> str | None:
        cwd = self.repo_working_dir(repo)

        if not cwd.exists() or not (cwd / ".git").exists():
            if repo.url:
                if cwd.exists():
                    shutil.rmtree(cwd, ignore_errors=True)
                await self._clone_repo(repo)
                cwd = self._clone_path(repo)
            else:
                return None

        token = await self.get_auth_token(repo)
        env: dict[str, str] = {}
        if token and repo.url:
            auth_url = self._auth_url(repo.url, token)
            env["GIT_ASKPASS"] = "echo"
            try:
                await self._run_git(cwd, ["git", "remote", "set-url", "origin", auth_url], env=env)
            except RuntimeError:
                await self._run_git(cwd, ["git", "remote", "add", "origin", auth_url], env=env)

        await self._run_git(cwd, ["git", "fetch", "origin", repo.default_branch], env=env)
        await self._run_git(cwd, ["git", "reset", "--hard", f"origin/{repo.default_branch}"], env=env)

        result = await self._run_git(cwd, ["git", "rev-parse", "HEAD"], env=env)
        return result.strip() if result else None

    def repo_working_dir(self, repo: Repository) -> Path:
        if repo.local_path:
            return Path(repo.local_path)
        return self._clone_path(repo)

    async def _clone_repo(self, repo: Repository) -> None:
        if not repo.url:
            return

        dest = self._clone_path(repo)
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)

        dest.parent.mkdir(parents=True, exist_ok=True)

        url = repo.url
        token = await self.get_auth_token(repo)
        if token:
            url = self._auth_url(repo.url, token)

        abs_dest = str(dest.resolve())
        cmd = ["git", "clone", "--branch", repo.default_branch, "--single-branch", url, abs_dest]
        await self._run_git(dest.parent, cmd)

    @staticmethod
    def _auth_url(url: str, token: str) -> str:
        parsed = urlparse(url)
        netloc = f"x-access-token:{token}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        authed = parsed._replace(netloc=netloc)
        return urlunparse(authed)

    @staticmethod
    async def _run_git(cwd: Path, cmd: list[str], env: dict[str, str] | None = None) -> str:
        import subprocess
        full_env = {**os.environ, **(env or {})}
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd, cwd=str(cwd), capture_output=True, env=full_env,
                    timeout=300,
                ),
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"git command timed out after 300s: {' '.join(cmd)}")
        if result.returncode != 0:
            logger.error("git command failed: %s\nstderr: %s", " ".join(cmd), result.stderr.decode())
            raise RuntimeError(f"git command failed: {result.stderr.decode()}")
        return result.stdout.decode()

    @staticmethod
    def _clone_path(repo: Repository) -> Path:
        return REPOS_BASE_DIR / str(repo.id)

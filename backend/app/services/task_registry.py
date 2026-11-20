import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    id: str
    repo_id: str
    kind: str
    status: str = "running"
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    task: asyncio.Task | None = None


class TaskRegistry:
    _tasks: dict[str, TaskInfo] = {}

    @classmethod
    def register(cls, repo_id: UUID, kind: str, task: asyncio.Task, message: str = "") -> str:
        task_id = str(uuid4())[:8]
        info = TaskInfo(
            id=task_id,
            repo_id=str(repo_id),
            kind=kind,
            message=message,
            task=task,
        )
        cls._tasks[task_id] = info
        task.add_done_callback(lambda t: cls._on_done(task_id, t))
        logger.info("Registered task %s: %s for repo %s", task_id, kind, repo_id)
        return task_id

    @classmethod
    def _on_done(cls, task_id: str, task: asyncio.Task) -> None:
        # Retrieve the task's exception so a crash that escaped the task body's
        # own try/except isn't swallowed into an "exception was never retrieved"
        # warning at GC time, which leaves the repo stuck in indexing/cloning
        # with no error surfaced anywhere.
        if not task.cancelled():
            try:
                exc = task.exception()
            except asyncio.CancelledError:
                exc = None
            if exc is not None:
                info = cls._tasks.get(task_id)
                kind = info.kind if info is not None else "?"
                logger.error(
                    "Background task %s (%s) crashed", task_id, kind, exc_info=exc,
                )
        # get_repo_tasks only ever surfaces 'running' tasks, so a finished task
        # has no further use; dropping it here is what keeps the registry
        # bounded.
        cls._tasks.pop(task_id, None)

    @classmethod
    def cancel(cls, task_id: str, repo_id: UUID | None = None) -> bool:
        """Cancel a running task; with ``repo_id``, only one of that repository."""
        info = cls._tasks.get(task_id)
        if not info or not info.task or info.task.done():
            return False
        if repo_id is not None and info.repo_id != str(repo_id):
            return False
        info.task.cancel()
        info.status = "cancelled"
        info.task = None
        logger.info("Cancelled task %s", task_id)
        return True

    @classmethod
    def get_repo_tasks(cls, repo_id: UUID) -> list[dict]:
        repo_id_str = str(repo_id)
        result = []
        for info in cls._tasks.values():
            if info.repo_id == repo_id_str and info.status == "running":
                result.append({
                    "id": info.id,
                    "kind": info.kind,
                    "status": info.status,
                    "message": info.message,
                    "created_at": info.created_at.isoformat(),
                })
        return result


    @classmethod
    def cancel_all(cls) -> None:
        for info in cls._tasks.values():
            if info.task and not info.task.done():
                info.task.cancel()
                info.status = "cancelled"
                info.task = None
        cls._tasks.clear()


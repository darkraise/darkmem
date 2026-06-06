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
        if len(cls._tasks) > 100:
            cls.cleanup_completed()
        task_id = str(uuid4())[:8]
        info = TaskInfo(
            id=task_id,
            repo_id=str(repo_id),
            kind=kind,
            message=message,
            task=task,
        )
        cls._tasks[task_id] = info
        task.add_done_callback(lambda t: cls._on_done(task_id))
        logger.info("Registered task %s: %s for repo %s", task_id, kind, repo_id)
        return task_id

    @classmethod
    def _on_done(cls, task_id: str) -> None:
        # Readers (get_repo_tasks / get_all_running) only ever surface 'running'
        # tasks, so a finished task has no further use; drop it immediately
        # instead of leaving a 'completed' entry that the >100-gated cleanup may
        # never reach (unbounded growth on low-volume deployments).
        cls._tasks.pop(task_id, None)

    @classmethod
    def cancel(cls, task_id: str) -> bool:
        info = cls._tasks.get(task_id)
        if not info or not info.task or info.task.done():
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
    def get_all_running(cls) -> list[dict]:
        return [
            {
                "id": info.id,
                "repo_id": info.repo_id,
                "kind": info.kind,
                "status": info.status,
                "message": info.message,
                "created_at": info.created_at.isoformat(),
            }
            for info in cls._tasks.values()
            if info.status == "running"
        ]

    @classmethod
    def cancel_all(cls) -> None:
        for info in cls._tasks.values():
            if info.task and not info.task.done():
                info.task.cancel()
                info.status = "cancelled"
                info.task = None
        cls._tasks.clear()

    @classmethod
    def cleanup_completed(cls) -> None:
        to_remove = [tid for tid, info in cls._tasks.items() if info.status != "running"]
        for tid in to_remove:
            del cls._tasks[tid]

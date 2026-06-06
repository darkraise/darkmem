"""Fire-and-forget background task helper.

``asyncio.create_task`` only holds a *weak* reference to the running task, so a
task whose return value isn't stored can be garbage-collected and silently
cancelled mid-run ("Task was destroyed but it is pending"). ``spawn`` keeps a
strong reference until the task finishes.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()


def spawn(coro, *, name: str | None = None) -> asyncio.Task:
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)

    def _done(t: asyncio.Task) -> None:
        _background_tasks.discard(t)
        if not t.cancelled():
            exc = t.exception()
            if exc is not None:
                logger.error("Background task %r failed: %s", name or t.get_name(), exc)

    task.add_done_callback(_done)
    return task

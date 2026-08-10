"""Resume as a specialised inject (T3.17, doc 15 §3.2).

At session start the latest checkpoint leads the managed block, so a fresh
session loads a budgeted digest instead of reloading full context.

**Resume is not a second inject path.** It is
:func:`app.services.inject_fill.fill` with the checkpoint passed as its
``lead`` — same budget, same marker safety, same stop-don't-skip rule. That is
the task's own done-when ("reuses the T3.10 budget path, not a parallel one"),
and it is load-bearing rather than tidy: a resume that computed its own budget
would exceed the operator's by exactly the checkpoint's size, and only on
sessions that had a checkpoint, which is the hardest shape to notice.

**A checkpoint carries no verification label** (T3.18). It is what an agent
said about its own run, not a claim any ladder judged, so it renders beside the
vault items wearing nothing that reads as a rung.
"""
from typing import Any, Protocol

from app.services.checkpoints import latest_checkpoint
from app.services.events import record_event
from app.services.inject_fill import FillResult, fill
from app.services.layer_composition import ComposedResult

__all__ = ["render_checkpoint", "resume_fill"]


class _Checkpoint(Protocol):
    summary: str
    next_steps: list


def render_checkpoint(checkpoint: _Checkpoint) -> str:
    """The resume digest, as one item.

    Labelled `resume` and nothing else: no layer tag, no verification status,
    no badge. A checkpoint is operational state, and a rung on it would be an
    unearned badge on unverified prose.
    """
    line = f"- (resume) {checkpoint.summary}"
    steps = [str(step) for step in (checkpoint.next_steps or []) if str(step).strip()]
    if steps:
        line += " Next: " + "; ".join(steps)
    return line


async def resume_fill(
    session: Any,
    *,
    result: ComposedResult,
    token_budget: int,
    origin_key: str | None,
    project: str = "default",
) -> FillResult:
    """The managed block's items for a resuming session.

    A missing checkpoint — no ``origin_key``, or a run with no saved
    checkpoint — degrades to the ordinary inject rather than erroring: a first
    session has nothing to resume from, which is the common case, not a fault.

    The ``resumed`` journal row is written only when a checkpoint was actually
    used, so the stream counts resumes rather than session starts.
    """
    checkpoint = None
    if origin_key:
        checkpoint = await latest_checkpoint(session, origin_key=origin_key, project=project)

    lead = render_checkpoint(checkpoint) if checkpoint is not None else None
    out = fill(result, token_budget=token_budget, lead=lead)

    # Journal the resume only if the digest survived the fill. A checkpoint the
    # budget refused, or one dropped for an embedded marker, was not resumed
    # from — recording it would put a resume in the stream that no session saw.
    if lead is not None and lead in out.items:
        await record_event(
            session,
            event_type="resumed",
            object_type="checkpoint",
            object_id=str(checkpoint.id),
            project=project,
            payload={"origin_key": origin_key, "tokens_used": out.tokens_used},
        )
    return out

from datetime import datetime

from pydantic import BaseModel, Field

from app.services.checkpoints import (
    MAX_NEXT_STEPS,
    MAX_STEP_LENGTH,
    MAX_SUMMARY_LENGTH,
)


class CheckpointCreate(BaseModel):
    """One agent run's note to its successor.

    The bounds are imported from the service rather than restated, so the
    422 this produces and the CHECK constraint that backs it cannot drift into
    two different limits — a payload the API accepted and the database refused
    would surface as a 500 on a request the caller was told was valid.
    """

    origin_key: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_LENGTH)
    next_steps: list[str] = Field(
        default_factory=list, max_length=MAX_NEXT_STEPS
    )
    project: str = Field(default="default", min_length=1, max_length=200)

    def bounded_steps(self) -> list[str]:
        """Per-step length, checked here because a list bound alone is not a
        payload bound: fifty steps of ten thousand characters each satisfies
        ``max_length`` and is not a compact checkpoint."""
        for step in self.next_steps:
            if len(step) > MAX_STEP_LENGTH:
                raise ValueError(
                    f"next_steps entries are bounded to {MAX_STEP_LENGTH} "
                    f"characters; one is {len(step)}"
                )
        return self.next_steps


class CheckpointResponse(BaseModel):
    id: str
    origin_key: str
    project: str
    summary: str
    next_steps: list[str]
    created_at: datetime | None

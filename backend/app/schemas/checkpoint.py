import json
from datetime import datetime

from pydantic import BaseModel, Field

from app.services.checkpoints import (
    MAX_NEXT_STEPS,
    MAX_STEP_LENGTH,
    MAX_SUMMARY_LENGTH,
    NEXT_STEPS_MAX_BYTES,
)


class CheckpointCreate(BaseModel):
    """One agent run's note to its successor.

    The bounds are imported from the service rather than restated. That was
    not enough on its own: the character bounds below and the database's
    `pg_column_size(next_steps) <= NEXT_STEPS_MAX_BYTES` were **born**
    different rather than drifted, so 15 steps of 500 CJK characters passed
    every check here and violated the CHECK at flush — a 500 on a request this
    validation had just called valid. `bounded_steps` now measures encoded
    size against the same constant the constraint uses, so the two cannot
    disagree about any payload.
    """

    origin_key: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_LENGTH)
    next_steps: list[str] = Field(
        default_factory=list, max_length=MAX_NEXT_STEPS
    )
    project: str = Field(default="default", min_length=1, max_length=200)

    def bounded_steps(self) -> list[str]:
        """Per-step length and total encoded size.

        Per-step because a list bound alone is not a payload bound: fifty
        steps of ten thousand characters each satisfies ``max_length``. Total
        *bytes* because that is what the database bounds — the JSONB encoding
        of non-ASCII text is several times its character count, which is how
        a payload well inside every character limit here still violated the
        CHECK.
        """
        for step in self.next_steps:
            if len(step) > MAX_STEP_LENGTH:
                raise ValueError(
                    f"next_steps entries are bounded to {MAX_STEP_LENGTH} "
                    f"characters; one is {len(step)}"
                )
        encoded = len(json.dumps(self.next_steps).encode("utf-8"))
        if encoded > NEXT_STEPS_MAX_BYTES:
            raise ValueError(
                f"next_steps encodes to {encoded} bytes; the bound is "
                f"{NEXT_STEPS_MAX_BYTES}. Non-ASCII text costs several bytes "
                f"per character, so a payload inside the per-step character "
                f"limit can still exceed it."
            )
        return self.next_steps


class CheckpointResponse(BaseModel):
    id: str
    origin_key: str
    project: str
    summary: str
    next_steps: list[str]
    created_at: datetime | None

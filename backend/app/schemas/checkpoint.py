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
    size against the same constant the constraint uses.

    **What that buys is one-directional, and saying "the two cannot disagree
    about any payload" overstated it** (branch review M-7, corrected
    2026-08-10). The two sides measure different things: `json.dumps` defaults
    to `ensure_ascii=True`, which renders a CJK character as a six-byte `\\uXXXX`
    escape where JSONB stores its three UTF-8 bytes, and `pg_column_size`
    reports the value *after* TOAST compression. So this check is
    systematically **larger** than what the constraint measures — about 2× on
    CJK text. That direction is the safe one and is deliberately kept: nothing
    this layer accepts can violate the CHECK, which is the property that
    matters, since the failure being prevented is a 500 on a request already
    called valid.

    The residue is that a payload the database would have accepted can be
    refused here, and the message quotes a byte count that is neither its
    UTF-8 length nor its stored size. Refusing something storable is a bounded
    annoyance; storing something the constraint rejects is a 500. The error
    text says which number it is quoting so the count is not mistaken for the
    stored size.
    """

    # Optional here, required by the *door*. A required field made the routes'
    # `body.origin_key or <X-Darkmem-Origin header>` fallback unreachable, so
    # the header the refusal message tells callers to send was documented on
    # both doors and honoured on neither — while capture's identical ladder
    # (`MemoryCreate.origin_key`, also optional) honoured it. The refusal that
    # matters is `resolve_checkpoint_origin`'s, which fires when neither the
    # field nor the header declares an identity, and which names both.
    origin_key: str | None = Field(default=None, max_length=500)
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
                f"next_steps encodes to {encoded} bytes with non-ASCII "
                f"escaped; the bound is {NEXT_STEPS_MAX_BYTES}. That count is "
                f"deliberately the conservative one — it runs larger than the "
                f"UTF-8 bytes the database actually stores, so nothing "
                f"accepted here can violate the CHECK. Non-ASCII text costs "
                f"several bytes per character either way, so a payload inside "
                f"the per-step character limit can still exceed it."
            )
        return self.next_steps


class CheckpointResponse(BaseModel):
    id: str
    origin_key: str
    project: str
    summary: str
    next_steps: list[str]
    created_at: datetime | None

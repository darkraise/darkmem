"""Distribution: the managed-block targets each client tool reads.

Doc 13 §6.5 puts distribution's *configuration* in Settings. This is its read:
the adapter registry, with the rows it refused. There is no inject writer, so
there is no policy to configure; a stored ``distribution_policy`` row from an
older build has no reader. Any future inject writer ships with a
server-enforced curb.

**Single-door (REST only), and that is a stated exception rather than an
oversight.** Invariant 17's parity applies to surfaces an agent uses; this one
describes what agents would be *told*. Recorded in the parity table with that
reason.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import SessionDep
from app.services.inject_adapters import get_registry

router = APIRouter(prefix="/api/v1/distribution", tags=["distribution"])


class DistributionTarget(BaseModel):
    tool: str
    context_file: str
    mcp_config: str


class RejectedTarget(BaseModel):
    tool: str
    reason: str


class DistributionState(BaseModel):
    targets: list[DistributionTarget]
    # Configured tools the registry refused. Served rather than logged-only:
    # an operator editing `inject_adapters` watched their row vanish from the
    # screen with the reason on the server, which is the same silent drop
    # invariant 14 forbids of retrieval.
    rejected: list[RejectedTarget] = []


@router.get("", response_model=DistributionState)
async def get_distribution(
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """Every target's block path, and the configured rows the registry refused.

    The targets come from T3.11's registry rather than a list here, so the tab
    shows what `darkmem connect` would actually use — a second list would be a
    screen that agrees with itself and not with the system.
    """
    adapters, rejected = await get_registry(session)
    return DistributionState(
        targets=[
            DistributionTarget(
                tool=adapter.tool,
                context_file=adapter.context_file,
                mcp_config=adapter.mcp_config,
            )
            for adapter in sorted(adapters.values(), key=lambda a: a.tool)
        ],
        rejected=[
            RejectedTarget(tool=tool, reason=reason)
            for tool, reason in sorted(rejected.items())
        ],
    )
